/* img-compress.js — comprime imágenes en el navegador antes de subirlas.
 *
 * Por qué: las fotos de celular (HEIC/JPEG de 24-48MP, 5-15MB) son pesadas
 * para subir por red móvil y lentas de procesar en el servidor. Acá las
 * redimensionamos a 1600px máx y las re-encodeamos a JPEG (~300KB):
 *   - iPhone: Safari decodifica HEIC nativamente → al servidor llega JPEG.
 *   - La subida es 10-30x más rápida y nunca pega el límite de tamaño.
 * Ante CUALQUIER falla se sube el archivo original (no rompe nada).
 */
(function () {
  var MAX_LADO = 1600;
  var CALIDAD = 0.85;
  var UMBRAL = 1.2 * 1024 * 1024; // por debajo de esto no tocamos el archivo

  function esHeic(file) {
    return /heic|heif/i.test(file.type) || /\.(heic|heif)$/i.test(file.name);
  }

  function comprimir(file) {
    var esImagen = /^image\//.test(file.type) || esHeic(file);
    // GIF no (perdería la animación); chicas no (no hace falta).
    if (!esImagen || file.type === 'image/gif') return Promise.resolve(file);
    if (file.size <= UMBRAL && !esHeic(file)) return Promise.resolve(file);

    return new Promise(function (resolve) {
      var url = URL.createObjectURL(file);
      var img = new Image();
      img.onload = function () {
        try {
          var lado = Math.max(img.naturalWidth, img.naturalHeight);
          var esc = Math.min(1, MAX_LADO / lado);
          var w = Math.max(1, Math.round(img.naturalWidth * esc));
          var h = Math.max(1, Math.round(img.naturalHeight * esc));
          var canvas = document.createElement('canvas');
          canvas.width = w; canvas.height = h;
          canvas.getContext('2d').drawImage(img, 0, 0, w, h);
          URL.revokeObjectURL(url);
          canvas.toBlob(function (blob) {
            // Si no mejoró (y no era HEIC), dejamos el original.
            if (!blob || (blob.size >= file.size && !esHeic(file))) return resolve(file);
            var base = (file.name || 'foto').replace(/\.[^.]+$/, '') || 'foto';
            resolve(new File([blob], base + '.jpg', { type: 'image/jpeg' }));
          }, 'image/jpeg', CALIDAD);
        } catch (e) { URL.revokeObjectURL(url); resolve(file); }
      };
      img.onerror = function () { URL.revokeObjectURL(url); resolve(file); };
      img.src = url;
    });
  }

  document.addEventListener('change', function (ev) {
    var input = ev.target;
    if (!input || input.tagName !== 'INPUT' || input.type !== 'file') return;
    if ((input.getAttribute('accept') || '').indexOf('image') === -1) return;
    if (!input.files || !input.files.length) return;
    if (!window.DataTransfer || !window.File) return; // navegador muy viejo: original

    var originales = Array.prototype.slice.call(input.files);
    Promise.all(originales.map(comprimir)).then(function (nuevos) {
      var cambio = nuevos.some(function (f, i) { return f !== originales[i]; });
      if (!cambio) return;
      try {
        var dt = new DataTransfer();
        nuevos.forEach(function (f) { dt.items.add(f); });
        input.files = dt.files; // no re-dispara 'change'
      } catch (e) { /* se sube el original */ }
    });
  }, true);
})();
