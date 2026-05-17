/**
 * Shared admin dashboard charts module.
 * Uses Chart.js to render professional charts on any admin overview page.
 */
const AdminCharts = (() => {
  let _charts = {};

  function _isDark() {
    return document.documentElement.classList.contains('dark');
  }

  function _colors() {
    const dark = _isDark();
    return {
      text: dark ? '#94a3b8' : '#475569',
      grid: dark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)',
      cardBg: dark ? '#1e293b' : '#ffffff',
      palette: ['#6366f1', '#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#8b5cf6'],
    };
  }

  function _legend(c) {
    return {
      position: 'bottom',
      labels: {
        color: c.text,
        padding: 14,
        font: { size: 12, family: 'Inter, sans-serif', weight: '500' },
        usePointStyle: true,
        pointStyleWidth: 8,
      },
    };
  }

  function _destroy(id) {
    if (_charts[id]) { _charts[id].destroy(); _charts[id] = null; }
  }

  /**
   * Doughnut chart
   */
  function doughnut(canvasId, labels, data, colors) {
    if (typeof Chart === 'undefined') return;
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    _destroy(canvasId);
    const c = _colors();
    _charts[canvasId] = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{
          data,
          backgroundColor: colors || c.palette.slice(0, labels.length),
          borderColor: c.cardBg,
          borderWidth: 3,
          hoverOffset: 8,
          hoverBorderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        cutout: '65%',
        plugins: {
          legend: _legend(c),
          tooltip: {
            backgroundColor: c.cardBg,
            titleColor: c.text,
            bodyColor: c.text,
            borderColor: _isDark() ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
            borderWidth: 1,
            cornerRadius: 8,
            padding: 10,
            bodyFont: { family: 'Inter, sans-serif' },
          },
        },
        animation: { animateRotate: true, duration: 800 },
      },
    });
  }

  /**
   * Bar chart
   */
  function bar(canvasId, labels, datasets) {
    if (typeof Chart === 'undefined') return;
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    _destroy(canvasId);
    const c = _colors();

    const chartDatasets = datasets.map((ds, i) => ({
      label: ds.label,
      data: ds.data,
      backgroundColor: ds.color || c.palette[i],
      borderRadius: 6,
      borderSkipped: false,
      barPercentage: 0.55,
      categoryPercentage: 0.7,
    }));

    _charts[canvasId] = new Chart(ctx, {
      type: 'bar',
      data: { labels, datasets: chartDatasets },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: _legend(c),
          tooltip: {
            backgroundColor: c.cardBg,
            titleColor: c.text,
            bodyColor: c.text,
            borderColor: _isDark() ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
            borderWidth: 1,
            cornerRadius: 8,
            padding: 10,
          },
        },
        scales: {
          x: {
            ticks: { color: c.text, font: { size: 12, family: 'Inter, sans-serif' } },
            grid: { display: false },
            border: { display: false },
          },
          y: {
            beginAtZero: true,
            ticks: {
              color: c.text,
              font: { size: 11, family: 'Inter, sans-serif' },
              stepSize: 1,
              padding: 8,
            },
            grid: { color: c.grid, drawBorder: false },
            border: { display: false },
          },
        },
        animation: { duration: 800 },
      },
    });
  }

  /**
   * Horizontal bar chart
   */
  function horizontalBar(canvasId, labels, data, colors) {
    if (typeof Chart === 'undefined') return;
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    _destroy(canvasId);
    const c = _colors();

    _charts[canvasId] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          data,
          backgroundColor: colors || c.palette.slice(0, labels.length),
          borderRadius: 6,
          borderSkipped: false,
          barPercentage: 0.6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        indexAxis: 'y',
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: c.cardBg,
            titleColor: c.text,
            bodyColor: c.text,
            borderColor: _isDark() ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
            borderWidth: 1,
            cornerRadius: 8,
            padding: 10,
          },
        },
        scales: {
          x: {
            beginAtZero: true,
            ticks: { color: c.text, font: { size: 11, family: 'Inter, sans-serif' }, stepSize: 1 },
            grid: { color: c.grid, drawBorder: false },
            border: { display: false },
          },
          y: {
            ticks: { color: c.text, font: { size: 12, family: 'Inter, sans-serif' }, padding: 8 },
            grid: { display: false },
            border: { display: false },
          },
        },
        animation: { duration: 800 },
      },
    });
  }

  return { doughnut, bar, horizontalBar };
})();
