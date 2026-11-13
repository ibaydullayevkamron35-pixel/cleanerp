// CleanERP — kichik yordamchi skriptlar
document.addEventListener('DOMContentLoaded', function () {
  // Xabarlar 6 soniyadan so'ng yopiladi (xatolar qoladi)
  document.querySelectorAll('.alert.auto-dismiss').forEach(function (el) {
    setTimeout(function () {
      if (window.bootstrap) { bootstrap.Alert.getOrCreateInstance(el).close(); }
    }, 6000);
  });

  // Filtr formasida tanlov o'zgarsa darhol yuborish
  document.querySelectorAll('.filter-bar select').forEach(function (sel) {
    sel.addEventListener('change', function () { sel.form.submit(); });
  });

  // Inspection formset: yangi mezon qo'shish
  var addBtn = document.getElementById('add-item-row');
  if (addBtn) {
    addBtn.addEventListener('click', function () {
      var total = document.getElementById('id_items-TOTAL_FORMS');
      var tpl = document.getElementById('empty-form');
      var tbody = document.getElementById('item-rows');
      if (!total || !tpl || !tbody) { return; }
      var idx = parseInt(total.value, 10);
      var html = tpl.innerHTML.replace(/__prefix__/g, idx);
      tbody.insertAdjacentHTML('beforeend', html);
      total.value = idx + 1;
    });
  }
});
