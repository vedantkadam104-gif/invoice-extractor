// Invoice Extractor Frontend JavaScript
let currentExtraction = null;
let selectedFile = null;

document.addEventListener('DOMContentLoaded', () => {
  initDropzone();
  initSampleButtons();
  initActions();
  checkHealth();
});

// Check API Health on load
async function checkHealth() {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    const pill = document.getElementById('ocr-status-pill');
    if (data.tesseract_detected) {
      pill.innerText = 'OCR: Tesseract Active';
      pill.style.borderColor = 'rgba(16, 185, 129, 0.4)';
    } else {
      pill.innerText = 'OCR: Smart PDF + Native';
    }
  } catch (err) {
    console.warn('Healthcheck error:', err);
  }
}

// Dropzone and file selection setup
function initDropzone() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const browseBtn = document.getElementById('browse-btn');
  const processBtn = document.getElementById('process-btn');
  const fileIndicator = document.getElementById('file-indicator');
  const dropzoneContent = dropzone.querySelector('.dropzone-content');
  const removeBtn = document.getElementById('remove-file-btn');

  browseBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
  });

  dropzone.addEventListener('click', () => {
    if (!selectedFile) fileInput.click();
  });

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragover');
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });

  removeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    resetFileSelection();
  });

  processBtn.addEventListener('click', () => {
    if (selectedFile) {
      uploadAndExtract(selectedFile);
    }
  });
}

function handleFileSelected(file) {
  selectedFile = file;
  document.getElementById('file-name').innerText = file.name;
  document.getElementById('file-size').innerText = (file.size / (1024 * 1024)).toFixed(2) + ' MB';
  document.getElementById('file-indicator').style.display = 'flex';
  document.querySelector('.dropzone-content').style.display = 'none';
  document.getElementById('process-btn').disabled = false;
}

function resetFileSelection() {
  selectedFile = null;
  document.getElementById('file-input').value = '';
  document.getElementById('file-indicator').style.display = 'none';
  document.querySelector('.dropzone-content').style.display = 'block';
  document.getElementById('process-btn').disabled = true;
}

// Upload & Extract Pipeline
async function uploadAndExtract(file) {
  const processBtn = document.getElementById('process-btn');
  const btnSpinner = document.getElementById('btn-spinner');
  const btnText = processBtn.querySelector('.btn-text');
  const stepProgress = document.getElementById('step-progress');
  const stepLabel = document.getElementById('step-label');

  // UI state: loading
  processBtn.disabled = true;
  btnSpinner.style.display = 'inline-block';
  btnText.innerText = 'Extracting...';
  stepProgress.style.display = 'block';
  stepLabel.innerText = 'Step 1/3: Reading bill & running OCR engine...';

  const formData = new FormData();
  formData.append('file', file);

  const model = document.getElementById('model-select').value;
  const apiKey = document.getElementById('api-key-input').value.trim();
  if (model) formData.append('model', model);
  if (apiKey) formData.append('openrouter_api_key', apiKey);

  setTimeout(() => {
    if (processBtn.disabled) {
      stepLabel.innerText = 'Step 2/3: Prompting OpenRouter LLM for structured JSON...';
    }
  }, 1500);

  setTimeout(() => {
    if (processBtn.disabled) {
      stepLabel.innerText = 'Step 3/3: Auditing arithmetic & detecting discrepancies...';
    }
  }, 3500);

  try {
    const response = await fetch('/api/extract', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({ detail: 'Extraction failed' }));
      throw new Error(errData.detail || `Server returned ${response.status}`);
    }

    const result = await response.json();
    currentExtraction = result;
    renderResults(result);

  } catch (error) {
    alert(`Extraction Error: ${error.message}`);
  } finally {
    processBtn.disabled = false;
    btnSpinner.style.display = 'none';
    btnText.innerText = 'Extract & Validate Data';
    stepProgress.style.display = 'none';
  }
}

// Render Results to UI
function renderResults(result) {
  const data = result.data;
  const val = result.validation;
  const curr = data.currency || '$';

  document.getElementById('empty-state').style.display = 'none';
  document.getElementById('results-content').style.display = 'block';
  document.getElementById('export-buttons').style.display = 'flex';

  // 1. Validation Banner
  const banner = document.getElementById('validation-banner');
  const valIcon = document.getElementById('val-icon');
  const valTitle = document.getElementById('val-title');
  const valExpl = document.getElementById('val-explanation');
  const valFlags = document.getElementById('val-flags');

  banner.className = 'validation-banner';
  valFlags.innerHTML = '';

  if (val.is_valid) {
    banner.classList.add('val-banner-valid');
    valIcon.innerText = '✅';
    valTitle.innerText = 'Math Audit Passed (No Hallucinations Detected)';
  } else if (val.status === 'MISMATCH_DETECTED') {
    banner.classList.add('val-banner-mismatch');
    valIcon.innerText = '⚠️';
    valTitle.innerText = `Arithmetic Discrepancy Flagged (${curr}${val.discrepancy_amount.toFixed(2)})`;
  } else {
    banner.classList.add('val-banner-warning');
    valIcon.innerText = 'ℹ️';
    valTitle.innerText = 'Audit Notice';
  }

  valExpl.innerText = val.explanation;
  if (val.flags && val.flags.length > 0) {
    val.flags.forEach(flag => {
      const badge = document.createElement('span');
      badge.className = 'flag-badge';
      badge.innerText = `• ${flag}`;
      valFlags.appendChild(badge);
    });
  }

  // 2. Metadata Grid
  document.getElementById('val-vendor').innerText = data.vendor_name || 'Not detected';
  document.getElementById('val-invoice-no').innerText = data.invoice_number || 'N/A';
  document.getElementById('val-date').innerText = data.invoice_date || 'N/A';
  document.getElementById('val-tax-id').innerText = data.vendor_tax_id || 'N/A';

  // 3. Line Items Table
  const tbody = document.getElementById('items-tbody');
  tbody.innerHTML = '';

  if (!data.items || data.items.length === 0) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td colspan="6" class="text-center" style="padding: 24px; color: var(--text-muted);">No line items detected.</td>`;
    tbody.appendChild(tr);
  } else {
    data.items.forEach((item, idx) => {
      const tr = document.createElement('tr');
      const expected = (item.quantity * item.unit_price);
      const isMatch = Math.abs(expected - item.total_price) <= 0.05;
      const matchBadge = isMatch 
        ? `<span class="badge-match">✓ Match</span>` 
        : `<span class="badge-diff">Diff: ${curr}${Math.abs(expected - item.total_price).toFixed(2)}</span>`;

      tr.innerHTML = `
        <td>${idx + 1}</td>
        <td><b>${escapeHtml(item.description)}</b></td>
        <td class="text-right">${item.quantity}</td>
        <td class="text-right">${curr}${item.unit_price.toFixed(2)}</td>
        <td class="text-right"><b>${curr}${item.total_price.toFixed(2)}</b></td>
        <td class="text-center">${matchBadge}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  // 4. Financials Summary
  document.getElementById('fin-subtotal').innerText = `${curr}${(data.subtotal || val.calculated_items_sum).toFixed(2)}`;
  document.getElementById('fin-tax-rate').innerText = data.tax_rate ? `${data.tax_rate}%` : 'Itemized';
  document.getElementById('fin-tax').innerText = `${curr}${(data.tax_amount || 0).toFixed(2)}`;
  document.getElementById('fin-discount').innerText = `-${curr}${(data.discount || 0).toFixed(2)}`;
  document.getElementById('fin-shipping').innerText = `${curr}${(data.shipping || 0).toFixed(2)}`;
  document.getElementById('fin-grand-total').innerText = `${curr}${data.grand_total.toFixed(2)}`;

  // 5. OCR & Performance Drawer
  document.getElementById('metric-ocr').innerText = result.ocr_engine_used;
  document.getElementById('metric-model').innerText = result.model_used;
  document.getElementById('metric-speed').innerText = `${result.processing_time_ms} ms`;
  document.getElementById('raw-ocr-display').innerText = result.raw_ocr_text;
}

// CSV & Excel Export Handlers
function initActions() {
  document.getElementById('download-csv-btn').addEventListener('click', async () => {
    if (!currentExtraction) return;
    try {
      const response = await fetch('/api/export/csv', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentExtraction)
      });
      const blob = await response.blob();
      downloadBlob(blob, `invoice_${currentExtraction.data.invoice_number || 'export'}.csv`);
    } catch (e) {
      alert('Failed to download CSV: ' + e.message);
    }
  });

  document.getElementById('download-excel-btn').addEventListener('click', async () => {
    if (!currentExtraction) return;
    try {
      const response = await fetch('/api/export/excel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentExtraction)
      });
      const blob = await response.blob();
      downloadBlob(blob, `invoice_${currentExtraction.data.invoice_number || 'export'}.xlsx`);
    } catch (e) {
      alert('Failed to download Excel: ' + e.message);
    }
  });

  document.getElementById('copy-json-btn').addEventListener('click', () => {
    if (!currentExtraction) return;
    navigator.clipboard.writeText(JSON.stringify(currentExtraction.data, null, 2));
    const btn = document.getElementById('copy-json-btn');
    const original = btn.innerText;
    btn.innerText = '✅ Copied!';
    setTimeout(() => { btn.innerText = original; }, 1800);
  });
}

function downloadBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.style.display = 'none';
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
}

// Built-in Sample Testers
function initSampleButtons() {
  document.getElementById('load-sample-valid').addEventListener('click', () => {
    const mockValid = {
      success: true,
      filename: "sample_valid_receipt.pdf",
      ocr_engine_used: "PyMuPDF (Digital PDF)",
      model_used: "google/gemini-2.0-flash-001",
      processing_time_ms: 1120.5,
      raw_ocr_text: "APEX OFFICE SUPPLIES\n124 Market Street, Seattle WA\nInvoice #: INV-2026-881\nDate: 2026-05-12\n\n1. Ergonomic Mesh Chair - Qty: 2 @ $150.00 = $300.00\n2. Dual Monitor Desk Stand - Qty: 1 @ $85.00 = $85.00\n3. Wireless Mechanical Keyboard - Qty: 2 @ $60.00 = $120.00\n\nSubtotal: $505.00\nSales Tax (10%): $50.50\nDiscount: $15.00\nGrand Total: $540.50\nThank you for your business!",
      data: {
        vendor_name: "Apex Office Supplies",
        vendor_address: "124 Market Street, Seattle WA",
        vendor_phone: "+1 (555) 234-5678",
        vendor_tax_id: "WA-8839210-A",
        invoice_number: "INV-2026-881",
        invoice_date: "2026-05-12",
        currency: "$",
        items: [
          { description: "Ergonomic Mesh Chair", quantity: 2, unit_price: 150.00, total_price: 300.00 },
          { description: "Dual Monitor Desk Stand", quantity: 1, unit_price: 85.00, total_price: 85.00 },
          { description: "Wireless Mechanical Keyboard", quantity: 2, unit_price: 60.00, total_price: 120.00 }
        ],
        subtotal: 505.00,
        tax_rate: 10.0,
        tax_amount: 50.50,
        discount: 15.00,
        shipping: 0.0,
        grand_total: 540.50
      },
      validation: {
        is_valid: true,
        status: "VALID",
        calculated_items_sum: 505.00,
        calculated_grand_total: 540.50,
        reported_grand_total: 540.50,
        discrepancy_amount: 0.0,
        flags: [],
        explanation: "Math Verified: All 3 line item(s) sum to $505.00. With tax ($50.50) and discount ($15.00), calculated total ($540.50) matches reported Grand Total ($540.50)."
      }
    };
    currentExtraction = mockValid;
    renderResults(mockValid);
  });

  document.getElementById('load-sample-mismatch').addEventListener('click', () => {
    const mockMismatch = {
      success: true,
      filename: "sample_tampered_bill.png",
      ocr_engine_used: "Tesseract OCR",
      model_used: "google/gemini-2.0-flash-001",
      processing_time_ms: 1340.2,
      raw_ocr_text: "METRO HARDWARE & CO.\nBill No: 99421\nDate: 2026-04-18\n\n1. Heavy Duty Cordless Drill - Qty: 1 @ $120.00 = $120.00\n2. 50-Piece Titanium Drill Bit Set - Qty: 2 @ $25.00 = $50.00\n\nSubtotal: $170.00\nTax: $15.00\nGrand Total: $250.00",
      data: {
        vendor_name: "Metro Hardware & Co.",
        invoice_number: "99421",
        invoice_date: "2026-04-18",
        currency: "$",
        items: [
          { description: "Heavy Duty Cordless Drill", quantity: 1, unit_price: 120.00, total_price: 120.00 },
          { description: "50-Piece Titanium Drill Bit Set", quantity: 2, unit_price: 25.00, total_price: 50.00 }
        ],
        subtotal: 170.00,
        tax_amount: 15.00,
        discount: 0.0,
        shipping: 0.0,
        grand_total: 250.00
      },
      validation: {
        is_valid: false,
        status: "MISMATCH_DETECTED",
        calculated_items_sum: 170.00,
        calculated_grand_total: 185.00,
        reported_grand_total: 250.00,
        discrepancy_amount: 65.00,
        flags: [
          "Grand Total Discrepancy: Expected $185.00 (Items: $170.00 + Tax: $15.00), but invoice states $250.00. Discrepancy: $65.00"
        ],
        explanation: "Discrepancy Detected ($65.00): Item sum is $170.00. Calculated final amount is $185.00, which does not match the reported Grand Total of $250.00. Please review the line items or OCR text for possible missed rows or tax misallocations."
      }
    };
    currentExtraction = mockMismatch;
    renderResults(mockMismatch);
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
