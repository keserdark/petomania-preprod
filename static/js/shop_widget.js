/* =====================================================
   shop_widget.js — Magazin global Petomania
   Integrat în base_joc.html
   ===================================================== */

(function() {

// ── State ──────────────────────────────────────────────────────────────
let _shopId       = null;
let _shopData     = null;
let _activeCat    = 0;
let _confirmItem  = null;
let _confirmQty   = 1;

// ── DOM refs (lazy) ────────────────────────────────────────────────────
function $id(id) { return document.getElementById(id); }

// ── Open / Close ───────────────────────────────────────────────────────
window.openShop = async function(shopId) {
    _shopId = shopId;
    _shopData = null;
    _activeCat = 0;

    const overlay = $id('shop-overlay');
    overlay.classList.add('open');

    // loading state
    $id('shop-grid').innerHTML = '<div style="color:var(--text-muted);font-style:italic;grid-column:1/-1;text-align:center;padding:32px 0">Se încarcă...</div>';
    $id('shop-tabs').innerHTML = '';
    $id('shop-header-name').textContent   = '...';
    $id('shop-header-npc').textContent    = '';
    $id('shop-dacoins-val').textContent   = '...';

    const resp = await fetch(`/joc/petomania/api/shop/${shopId}`);
    const data = await resp.json();
    if (!data.ok) {
        $id('shop-grid').innerHTML = `<div style="color:var(--danger);grid-column:1/-1;text-align:center;padding:32px 0">${data.error}</div>`;
        return;
    }

    _shopData = data.shop;
    _renderShop(data.dacoins);
};

window.closeShop = function() {
    $id('shop-overlay').classList.remove('open');
    _closeConfirm();
    _shopId   = null;
    _shopData = null;
};

// ── Render ─────────────────────────────────────────────────────────────
function _renderShop(dacoins) {
    const s = _shopData;
    $id('shop-header-icon').textContent  = s.npc_icon;
    $id('shop-header-name').textContent  = s.name;
    $id('shop-header-npc').textContent   = s.npc;
    $id('shop-dacoins-val').textContent  = dacoins.toLocaleString();

    // Tabs
    const tabBar = $id('shop-tabs');
    tabBar.innerHTML = '';
    s.categories.forEach((cat, i) => {
        const btn = document.createElement('button');
        btn.className = 'shop-tab' + (i === _activeCat ? ' active' : '');
        btn.textContent = cat.name;
        btn.onclick = () => _switchTab(i);
        tabBar.appendChild(btn);
    });

    _renderGrid();
}

function _switchTab(idx) {
    _activeCat = idx;
    _closeConfirm();
    document.querySelectorAll('.shop-tab').forEach((t, i) => {
        t.classList.toggle('active', i === idx);
    });
    _renderGrid();
}

function _renderGrid() {
    const cat   = _shopData.categories[_activeCat];
    const grid  = $id('shop-grid');
    grid.innerHTML = '';

    const items = cat.items;
    // 10 sloturi — 2 randuri de 5
    for (let i = 0; i < 10; i++) {
        const slot = document.createElement('div');
        if (i < items.length) {
            const item = items[i];
            slot.className = 'shop-slot';
            const iconHtml = item.img
                ? `<img class="shop-slot-img" src="${item.img}" alt="${item.name}">`
                : `<span class="shop-slot-icon">${item.icon}</span>`;
            slot.innerHTML = `
                ${iconHtml}
                <span class="shop-slot-name">${item.name}</span>
                <span class="shop-slot-price">✦ ${item.price.toLocaleString()}</span>
            `;
            slot.onclick = () => _openConfirm(item);
        } else {
            slot.className = 'shop-slot empty';
            slot.innerHTML = '<span style="font-size:20px;opacity:0.3">○</span>';
        }
        grid.appendChild(slot);
    }
}

// ── Confirmare cumpărare ───────────────────────────────────────────────
function _openConfirm(item) {
    _confirmItem = item;
    _confirmQty  = 1;

    if (item.img) {
        $id('shop-confirm-icon').innerHTML = `<img src="${item.img}" style="width:56px;height:56px;object-fit:contain;">`;
    } else {
        $id('shop-confirm-icon').textContent = item.icon;
    }
    $id('shop-confirm-name').textContent = item.name;
    $id('shop-confirm-desc').textContent = item.desc;
    $id('shop-confirm-msg').textContent  = '';
    $id('shop-confirm-msg').className    = 'shop-confirm-msg';
    _updateConfirmTotal();

    $id('shop-confirm-overlay').classList.add('open');
}

function _closeConfirm() {
    $id('shop-confirm-overlay').classList.remove('open');
    _confirmItem = null;
    _confirmQty  = 1;
}

function _updateConfirmTotal() {
    if (!_confirmItem) return;
    $id('shop-qty-display').textContent  = _confirmQty;
    $id('shop-confirm-total').textContent = `Total: ✦ ${(_confirmItem.price * _confirmQty).toLocaleString()} Dacoins`;
}

window.shopQtyChange = function(delta) {
    _confirmQty = Math.max(1, Math.min(12, _confirmQty + delta));
    _updateConfirmTotal();
};

window.shopCancelConfirm = function() { _closeConfirm(); };

window.shopConfirmBuy = async function() {
    if (!_confirmItem) return;

    const btn = $id('shop-buy-btn');
    btn.disabled   = true;
    btn.textContent = '...';

    const resp = await fetch(`/joc/petomania/api/shop/${_shopId}/buy`, {
        method:  'POST',
        headers: {'Content-Type': 'application/json'},
        body:    JSON.stringify({
            category: _confirmItem.category,
            item_key: _confirmItem.item_key,
            qty:      _confirmQty,
        })
    });
    const data = await resp.json();

    btn.disabled   = false;
    btn.textContent = 'Cumpără';

    const msgEl = $id('shop-confirm-msg');
    if (data.ok) {
        msgEl.className   = 'shop-confirm-msg success';
        msgEl.textContent = `✓ ${data.qty}× ${data.item_name} cumpărat!`;
        // Actualizeaza dacoins in header shop si in navbar
        $id('shop-dacoins-val').textContent = data.balance.toLocaleString();
        const globalDacoins = document.getElementById('rb-dacoins');
        if (globalDacoins) globalDacoins.textContent = data.balance.toLocaleString();
        // Actualizeaza si in topbar daca exista
        document.querySelectorAll('.pet-dacoins-val').forEach(el => {
            el.textContent = data.balance.toLocaleString();
        });
        setTimeout(_closeConfirm, 1200);
    } else {
        msgEl.className   = 'shop-confirm-msg error';
        msgEl.textContent = data.error;
    }
};

// ── Inchide la click pe overlay ────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    $id('shop-overlay').addEventListener('click', (e) => {
        if (e.target === $id('shop-overlay')) closeShop();
    });
    $id('shop-confirm-overlay').addEventListener('click', (e) => {
        if (e.target === $id('shop-confirm-overlay')) _closeConfirm();
    });
});

})();
