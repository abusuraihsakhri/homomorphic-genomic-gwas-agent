'use strict';
// All statistics run in the browser. This is plaintext, NOT homomorphic encryption.
(function () {
  const $ = id => document.getElementById(id);
  let batchRows = [];
  const FIELDS = ['case_alt', 'case_ref', 'control_alt', 'control_ref'];

  // Stable complementary error function approximation (Numerical Recipes).
  function erfc(x) {
    const t = 1 / (1 + 0.5 * x);
    return t * Math.exp(-x * x - 1.26551223 + t * (1.00002368 + t *
      (0.37409196 + t * (0.09678418 + t * (-0.18628806 + t *
      (0.27886807 + t * (-1.13520398 + t * (1.48851587 + t *
      (-0.82215223 + t * 0.17087277)))))))));
  }

  function count(value) {
    const valueText = String(value).trim();
    if (!/^(0|[1-9]\d*)$/.test(valueText)) throw new Error('Allele counts must be non-negative whole numbers.');
    const n = Number(valueText);
    if (!Number.isSafeInteger(n)) throw new Error('An allele count exceeds JavaScript safe integer precision.');
    return n;
  }

  function testAssociation(input) {
    const [a, b, c, d] = input.map(count);
    const r1 = a + b, r2 = c + d, c1 = a + c, c2 = b + d, n = r1 + r2;
    if (!(r1 && r2 && c1 && c2)) throw new Error('Both groups and both alleles must have positive totals.');
    if (n > 1e12) throw new Error('Total allele count exceeds the 1e12 precision limit.');
    const determinant = a * d - b * c;
    const chi = n * determinant * determinant / (r1 * r2 * c1 * c2);
    const expected = [r1*c1/n, r1*c2/n, r2*c1/n, r2*c2/n];
    if (!Number.isFinite(chi)) throw new Error('Unable to calculate a finite chi-square statistic.');
    return {
      chi_square: chi,
      p_value: Math.max(0, Math.min(1, erfc(Math.sqrt(chi / 2)))),
      odds_ratio: b*c ? a*d/(b*c) : null,
      sparse_expected_counts: expected.some(v => v < 5)
    };
  }
  function fmt(x) { return x === null ? 'Undefined' : Number(x).toPrecision(5); }
  function csvCell(raw) {
    let value = String(raw);
    // Prevent formula execution when exported CSV is opened in spreadsheets.
    if (/^[\s]*[=+@\-\t\r]/.test(value)) value = "'" + value;
    return '"' + value.replace(/"/g, '""') + '"';
  }
  function download(name, contents) {
    const url = URL.createObjectURL(new Blob([contents], {type:'text/csv;charset=utf-8'}));
    const anchor = document.createElement('a');
    anchor.href = url; anchor.download = name;
    document.body.append(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  // Quoted fields, doubled quotes, and CR/LF. Reject unterminated quoted data.
  function parseCSV(text) {
    const rows = []; let row = [], cell = '', quoted = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (quoted) {
        if (ch === '"' && text[i + 1] === '"') {cell += '"'; i++;}
        else if (ch === '"') quoted = false;
        else cell += ch;
      } else if (ch === '"' && cell === '') quoted = true;
      else if (ch === ',') {row.push(cell); cell = '';}
      else if (ch === '\n' || ch === '\r') {
        if (ch === '\r' && text[i + 1] === '\n') i++;
        row.push(cell); rows.push(row); row = []; cell = '';
      } else cell += ch;
    }
    if (quoted) throw new Error('Malformed CSV: unterminated quoted field.');
    if (row.length || cell) {row.push(cell); rows.push(row);}
    return rows.filter(r => !(r.length === 1 && r[0].trim() === ''));
  }

  function calcSingle(e) {
    e.preventDefault(); $('single-error').hidden = true;
    try {
      const result = testAssociation([$('case-alt').value, $('case-ref').value, $('control-alt').value, $('control-ref').value]);
      $('chi-stat').textContent = fmt(result.chi_square);
      $('p-stat').textContent = fmt(result.p_value);
      $('odds-stat').textContent = fmt(result.odds_ratio);
      $('result-note').textContent = result.sparse_expected_counts
        ? 'Warning: at least one expected cell count is below 5; the asymptotic p-value may be unreliable.'
        : 'All expected cell counts are at least 5. Unadjusted allelic association only.';
      $('result').hidden = false;
    } catch(err) { $('result').hidden = true; $('single-error').textContent = err.message; $('single-error').hidden = false; }
  }

  async function loadBatch() {
    $('batch-result').hidden = true; batchRows = [];
    const file = $('csv-file').files[0]; if (!file) return;
    if (file.size > 2000000) { $('batch-status').textContent = 'Error: CSV exceeds 2 MB limit.'; return; }
    $('batch-status').textContent = 'Reading file locally…';
    try {
      const rows = parseCSV((await file.text()).replace(/^\uFEFF/, ''));
      if (!rows.length) throw new Error('CSV is empty.');
      const headers = rows.shift().map(x => x.trim().toLowerCase());
      const allFields = ['variant_id', ...FIELDS];
      const indexes = allFields.map(x => headers.indexOf(x));
      if (indexes.includes(-1)) throw new Error('Missing CSV columns: ' + allFields.filter((_,i) => indexes[i] === -1).join(', '));
      if (rows.length > 10000) throw new Error('More than 10,000 data rows. Split the CSV into smaller files.');
      const errors = [];
      rows.forEach((row, i) => {
        try {
          if (row.length !== headers.length) throw new Error('Column count mismatch');
          const variant_id = row[indexes[0]].trim();
          if (!variant_id) throw new Error('Empty variant identifier');
          const inputs = indexes.slice(1).map(index => row[index]);
          batchRows.push({variant_id, ...testAssociation(inputs)});
        } catch(err) {
          if (errors.length < 5) errors.push('Row ' + (i+2) + ': ' + err.message);
        }
      });
      const invalid = rows.length - batchRows.length;
      $('batch-status').textContent = batchRows.length + ' variants analyzed; ' + invalid + ' invalid row(s).' +
        (errors.length ? ' ' + errors.join(' | ') : '');
      const tbody = $('results-body'); tbody.replaceChildren();
      batchRows.slice(0,100).forEach(result => {
        const tr = document.createElement('tr');
        [result.variant_id, fmt(result.chi_square), fmt(result.p_value), fmt(result.odds_ratio), result.sparse_expected_counts ? 'Yes' : 'No']
          .forEach(value => {const td = document.createElement('td'); td.textContent = value; tr.append(td);});
        tbody.append(tr);
      });
      $('batch-count').textContent = batchRows.length + ' valid variants';
      $('batch-limit-note').textContent = batchRows.length > 100 ? 'Showing first 100 variants. CSV export contains all results.' : '';
      $('batch-result').hidden = batchRows.length === 0;
    } catch(err) { $('batch-status').textContent = 'Error: ' + err.message; }
  }

  $('single-form').addEventListener('submit', calcSingle);
  $('reset-form').addEventListener('click', () => {
    [['case-alt',30],['case-ref',70],['control-alt',15],['control-ref',85]].forEach(([id,n]) => $(id).value = n);
    $('single-error').hidden = true; $('result').hidden = true;
  });
  $('csv-file').addEventListener('change', loadBatch);
  $('download-sample').addEventListener('click', () => download('sample-allele-counts.csv',
    'variant_id,case_alt,case_ref,control_alt,control_ref\nrsExample1,30,70,15,85\nrsExample2,25,75,50,150\n'));
  $('export-results').addEventListener('click', () => {
    const header = ['variant_id', 'chi_square', 'p_value', 'odds_ratio', 'sparse_expected_counts'];
    const values = batchRows.map(r => header.map(key => csvCell(r[key] === null ? '' : r[key])).join(','));
    download('allelic-association-results.csv', header.join(',') + '\n' + values.join('\n') + '\n');
  });
})();
