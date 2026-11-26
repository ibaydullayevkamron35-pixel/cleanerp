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
  // Ro'yxat ichidagi kichik formada Enter bosilsa butun forma yuborilmasin (yozilgan narsa yo'qolmasin)
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter') { return; }
    var t = e.target;
    if (!t || !t.closest || !t.closest('.dd-single, .dd-multi')) { return; }
    if (t.tagName === 'BUTTON' || t.tagName === 'TEXTAREA') { return; }
    e.preventDefault();
    var qf = t.closest('.q-form, .dd-quick-form');
    if (qf) { var sv = qf.querySelector('.q-save, .dd-quick-save'); if (sv) { sv.click(); } return; }
    if (t.type === 'search') {
      var opts = t.closest('.dd-menu').querySelectorAll('.dd-opt');
      for (var i = 0; i < opts.length; i++) {
        if (!opts[i].hidden && opts[i].dataset.value !== '') { opts[i].click(); break; }
      }
    }
  }, true);

  // Galochkali bitta tanlov (mijoz, holat va h.k.): tanlangani piychka bilan, tanlangach yopiladi
  document.querySelectorAll('form.card-body select.form-select:not([multiple])').forEach(function (sel) {
    if (!window.bootstrap || sel.closest('table')) { return; }
    var form = sel.form;
    var clientSel = form ? form.querySelector('select[name=client]') : null;
    var mapEl = document.getElementById('owner-map');
    var owners = {};
    try { owners = (mapEl && JSON.parse(mapEl.textContent)[sel.name]) || {}; } catch (e) {}
    var wrap = document.createElement('div');
    wrap.className = 'dd-single dropdown';
    var btn = document.createElement('button');
    btn.type = 'button'; btn.className = 'form-select text-start dd-toggle';
    if (sel.classList.contains('is-invalid')) { btn.classList.add('is-invalid'); }
    btn.setAttribute('data-bs-toggle', 'dropdown'); btn.setAttribute('data-bs-auto-close', 'outside'); btn.setAttribute('aria-expanded', 'false');
    var menu = document.createElement('div');
    menu.className = 'dropdown-menu w-100 p-1 dd-menu';
    var search = null;
    if (sel.options.length > 8) {
      search = document.createElement('input');
      search.type = 'search'; search.placeholder = 'Qidirish...'; search.className = 'form-control form-control-sm mb-1';
      menu.appendChild(search);
    }
    var list = document.createElement('div');
    list.className = 'dd-list';
    menu.appendChild(list);
    var opts = [];
    function addItem(o) {
      var a = document.createElement('button');
      a.type = 'button'; a.className = 'dropdown-item d-flex align-items-center justify-content-between dd-opt';
      a.dataset.value = o.value;
      var t = document.createElement('span'); t.textContent = o.value === '' ? 'Tanlanmagan' : o.text;
      var ck = document.createElement('i'); ck.className = 'bi bi-check2 text-success ms-2';
      a.appendChild(t); a.appendChild(ck);
      a.addEventListener('click', function () {
        sel.value = o.value;
        sel.dispatchEvent(new Event('change', { bubbles: true }));
        paint();
        bootstrap.Dropdown.getOrCreateInstance(btn).hide();
      });
      list.appendChild(a);
      opts.push(a);
    }
    Array.prototype.forEach.call(sel.options, function (o) { addItem(o); });
    function paint() {
      var cur = sel.options[sel.selectedIndex];
      btn.textContent = cur && cur.value !== '' ? cur.text : 'Tanlang';
      btn.classList.toggle('text-muted', !cur || cur.value === '');
      opts.forEach(function (a) {
        var on = a.dataset.value === sel.value;
        a.classList.toggle('active-opt', on);
        a.querySelector('i').style.visibility = on ? 'visible' : 'hidden';
      });
    }

    // Forma ichidan chiqmasdan yangi mijoz / obyekt qo'shish
    var Q = null;
    if (sel.name === 'client' && form && form.dataset.clientQuick) {
      Q = { url: form.dataset.clientQuick, title: "Yangi mijoz qo'shish", fields: [
        { key: 'kind', type: 'select', opts: [['individual', 'Jismoniy shaxs'], ['legal', 'Yuridik shaxs']] },
        { key: 'name', ph: 'F.I.Sh. / Kompaniya nomi' }, { key: 'phone', ph: 'Telefon (+998...)' }] };
    } else if (sel.name === 'facility' && clientSel && form && form.dataset.facilityQuick) {
      Q = { url: form.dataset.facilityQuick, title: "Yangi obyekt qo'shish", needClient: true, fields: [
        { key: 'name', ph: 'Obyekt nomi' }, { key: 'address', ph: 'Manzil' }] };
    }
    if (Q) {
      var qb = document.createElement('div');
      qb.className = 'border-top mt-1 pt-2 px-2 pb-1';
      var html = '<button type="button" class="btn btn-sm btn-outline-primary w-100 q-open"><i class="bi bi-plus-lg me-1"></i>' + Q.title + '</button><div class="q-form" hidden>';
      Q.fields.forEach(function (f) {
        if (f.type === 'select') {
          html += '<select class="form-select form-select-sm mb-1" data-k="' + f.key + '">' +
            f.opts.map(function (o) { return '<option value="' + o[0] + '">' + o[1] + '</option>'; }).join('') + '</select>';
        } else {
          html += '<input class="form-control form-control-sm mb-1" data-k="' + f.key + '" placeholder="' + f.ph + '">';
        }
      });
      html += '<div class="text-danger small q-err" hidden></div><button type="button" class="btn btn-sm btn-primary w-100 q-save">Saqlash va tanlash</button></div>';
      qb.innerHTML = html;
      menu.appendChild(qb);
      var qf = qb.querySelector('.q-form'), err = qb.querySelector('.q-err');
      qb.addEventListener('click', function (e) { e.stopPropagation(); });
      qb.querySelector('.q-open').addEventListener('click', function () {
        qf.hidden = !qf.hidden;
        if (!qf.hidden) { qb.querySelector('input').focus(); qb.scrollIntoView({ block: 'nearest' }); }
      });
      qb.querySelector('.q-save').addEventListener('click', function () {
        var csrf = document.querySelector('input[name=csrfmiddlewaretoken]');
        var data = {};
        qb.querySelectorAll('[data-k]').forEach(function (el) { data[el.dataset.k] = el.value; });
        if (Q.needClient) {
          if (!clientSel.value) { err.textContent = 'Avval mijozni tanlang.'; err.hidden = false; return; }
          data.client = clientSel.value;
        }
        fetch(Q.url, { method: 'POST', headers: { 'X-CSRFToken': csrf ? csrf.value : '' }, body: new URLSearchParams(data) })
          .then(function (r) { return r.json().then(function (d) { return [r.ok, d]; }); })
          .then(function (res) {
            if (!res[0]) { err.textContent = res[1].error || 'Xatolik'; err.hidden = false; return; }
            err.hidden = true;
            var o = new Option(res[1].label, res[1].id);
            sel.add(o);
            if (res[1].client) { owners[String(res[1].id)] = res[1].client; }
            addItem(o);
            sel.value = o.value;
            sel.dispatchEvent(new Event('change', { bubbles: true }));
            paint();
            qb.querySelectorAll('input').forEach(function (el) { el.value = ''; });
            qf.hidden = true;
            bootstrap.Dropdown.getOrCreateInstance(btn).hide();
          })
          .catch(function () { err.textContent = 'Server bilan aloqa yo\'q.'; err.hidden = false; });
      });
    }

    if (search) {
      search.addEventListener('input', function () {
        var q = search.value.toLowerCase();
        opts.forEach(function (a) { a.hidden = a.textContent.toLowerCase().indexOf(q) === -1; });
      });
    }
    sel.addEventListener('change', paint);
    sel.style.display = 'none';
    sel.insertAdjacentElement('afterend', wrap);
    wrap.appendChild(btn); wrap.appendChild(menu);
    paint();
    // Mijoz tanlanganda obyekt / shartnoma / buyurtma ro'yxatini shu mijozga tegishlisi bilan cheklash
    if (clientSel && sel !== clientSel && (Object.keys(owners).length || sel.name === 'facility')) {
      var filt = function () {
        var c = clientSel.value;
        opts.forEach(function (a) {
          var v = a.dataset.value;
          a.hidden = !(v === '' || !c || String(owners[v]) === c);
        });
        Array.prototype.forEach.call(sel.options, function (o) {
          o.hidden = o.value !== '' && !!c && String(owners[o.value]) !== c;
        });
        var cur = sel.options[sel.selectedIndex];
        if (cur && cur.value !== '' && c && String(owners[cur.value]) !== c) { sel.value = ''; paint(); }
      };
      clientSel.addEventListener('change', filt);
      filt();
    }
  });

  // Galochkali ko'p tanlov (brigada, xodim, obyekt)
  document.querySelectorAll('.dd-multi').forEach(function (box) {
    var label = box.querySelector('.dd-label');
    var items = box.querySelectorAll('.dd-item');
    var empty = box.querySelector('.dd-empty');
    function refresh() {
      var names = [];
      box.querySelectorAll('input:checked').forEach(function (i) {
        names.push(i.nextElementSibling.textContent.trim());
      });
      label.classList.toggle('text-muted', names.length === 0);
      label.textContent = names.length === 0 ? 'Tanlang' :
        (names.length <= 2 ? names.join(', ') : names.length + ' ta tanlandi: ' + names.slice(0, 2).join(', ') + '...');
    }
    box.addEventListener('change', refresh);
    refresh();
    var qurl = box.dataset.quickUrl;
    if (qurl) {
      var openBtn = box.querySelector('.dd-quick-open'), qf = box.querySelector('.dd-quick-form');
      openBtn.addEventListener('click', function () { qf.hidden = !qf.hidden; });
      box.querySelector('.dd-quick-save').addEventListener('click', function () {
        var err = box.querySelector('.q-err'), clientSel = document.getElementById(box.dataset.filterBy);
        var csrf = document.querySelector('input[name=csrfmiddlewaretoken]');
        var body = new URLSearchParams({
          client: clientSel ? clientSel.value : '', name: box.querySelector('.q-name').value,
          address: box.querySelector('.q-address').value, kind: box.querySelector('.q-kind').value
        });
        fetch(qurl, { method: 'POST', headers: { 'X-CSRFToken': csrf ? csrf.value : '' }, body: body })
          .then(function (r) { return r.json().then(function (d) { return [r.ok, d]; }); })
          .then(function (res) {
            if (!res[0]) { err.textContent = res[1].error || 'Xatolik'; err.hidden = false; return; }
            err.hidden = true;
            var lab = document.createElement('label');
            lab.className = 'dropdown-item dd-item d-flex align-items-center gap-2';
            lab.dataset.owner = res[1].client;
            var inp = document.createElement('input');
            inp.type = 'checkbox'; inp.className = 'form-check-input mt-0'; inp.checked = true;
            inp.name = box.querySelector('input[type=checkbox]') ? box.querySelector('input[type=checkbox]').name : 'facilities';
            inp.value = res[1].id;
            var sp = document.createElement('span'); sp.textContent = res[1].label;
            lab.appendChild(inp); lab.appendChild(document.createTextNode(' ')); lab.appendChild(sp);
            box.querySelector('.dd-empty').insertAdjacentElement('beforebegin', lab);
            box.querySelector('.dd-empty').hidden = true;
            box.querySelector('.q-name').value = ''; box.querySelector('.q-address').value = '';
            qf.hidden = true;
            items = box.querySelectorAll('.dd-item');
            refresh();
          });
      });
    }
    var src = box.dataset.filterBy ? document.getElementById(box.dataset.filterBy) : null;
    if (src) {
      var apply = function (reset) {
        var shown = 0;
        items.forEach(function (it) {
          var ok = !src.value || it.dataset.owner === src.value;
          it.hidden = !ok;
          it.classList.toggle('d-none', !ok);
          if (!ok) { it.querySelector('input').checked = false; } else { shown++; }
        });
        if (empty) { empty.hidden = shown !== 0; }
        refresh();
      };
      src.addEventListener('change', apply);
      apply();
    }
  });
});
