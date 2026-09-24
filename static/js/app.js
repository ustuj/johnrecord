(() => {
  const role = document.body.dataset.role;
  const search = document.querySelector('#catalog-search');
  const supplier = document.querySelector('#supplier-filter');
  const sort = document.querySelector('#stock-sort');
  const grid = document.querySelector('#catalog-grid');
  const count = document.querySelector('#result-count');
  const section = new URLSearchParams(window.location.search).get('section') || '';

  if ((role === 'manager' || role === 'admin') && grid) {
    const saved_sort = localStorage.getItem('vinyl_stock_sort') || '';
    if (sort && !sort.value && saved_sort) {
      sort.value = saved_sort;
    }

    let timeout_id = 0;

    async function refresh_catalog() {
      const params = new URLSearchParams();
      params.set('q', search?.value || '');
      params.set('supplier', supplier?.value || '');
      params.set('stock_sort', sort?.value || '');
      if (section) {
        params.set('section', section);
      }

      try {
        const response = await fetch(`/api/catalog?${params.toString()}`, {
          headers: {'X-Requested-With': 'XMLHttpRequest'},
        });
        if (!response.ok) {
          return;
        }
        grid.innerHTML = await response.text();
        if (count) {
          count.textContent = String(grid.querySelectorAll('.product-card').length);
        }
        window.history.replaceState({}, '', `/catalog?${params.toString()}`);
      } catch (_error) {
        // Сетевые ошибки не должны приводить к аварийному завершению интерфейса.
      }
    }

    function schedule_refresh() {
      window.clearTimeout(timeout_id);
      timeout_id = window.setTimeout(refresh_catalog, 140);
    }

    search?.addEventListener('input', schedule_refresh);
    supplier?.addEventListener('change', schedule_refresh);
    sort?.addEventListener('change', () => {
      localStorage.setItem('vinyl_stock_sort', sort.value);
      schedule_refresh();
    });
  }
})();
