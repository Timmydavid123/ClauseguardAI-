/* ─── ClauseGuard Main JS ─── */

// ── DRAG & DROP ───────────────────────────────────────────────────────────────
const dropZone  = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');

if (dropZone) {
  dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault(); dropZone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) handleFileUpload(file);
  });
}
if (fileInput) fileInput.addEventListener('change', e => { if (e.target.files[0]) handleFileUpload(e.target.files[0]); });

// ── CHAR COUNT ────────────────────────────────────────────────────────────────
const textarea  = document.getElementById('contract-text');
const charCount = document.getElementById('char-count');
if (textarea && charCount) {
  textarea.addEventListener('input', () => {
    const len = textarea.value.length;
    charCount.textContent = `${len.toLocaleString()} character${len !== 1 ? 's' : ''}`;
  });
}

// ── GET CSRF TOKEN FROM COOKIE ────────────────────────────────────────────────
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// ── FILE VALIDATION ───────────────────────────────────────────────────────────
function isValidDocumentType(file) {
    const validTypes = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'application/rtf',
        'application/vnd.oasis.opendocument.text',
        'application/octet-stream'
    ];
    
    const validExtensions = ['.pdf', '.docx', '.doc', '.txt', '.rtf', '.odt'];
    const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    const fileType = file.type || '';
    
    return validTypes.includes(fileType) || validExtensions.includes(fileExtension);
}

// ── POLL TASK STATUS ───────────────────────────────────────────────────────────
let pollInterval = null;

function pollTaskStatus(taskId) {
  let pollCount = 0;
  const maxPolls = 300; // 10 minutes max (2s * 300 = 600s = 10min)
  
  // Clear any existing poll interval
  if (pollInterval) {
    clearInterval(pollInterval);
  }
  
  pollInterval = setInterval(async () => {
    pollCount++;
    
    try {
      const res = await fetch(`/task-status/${taskId}/`);
      const data = await res.json();
      
      // Update loading message based on status
      updateLoadingMessage(data);
      
      if (data.status === 'SUCCESS') {
        clearInterval(pollInterval);
        pollInterval = null;
        showLoadingComplete();
        setTimeout(() => {
          window.location.href = data.redirect;
        }, 800);
      } else if (data.status === 'FAILURE') {
        clearInterval(pollInterval);
        pollInterval = null;
        hideLoading();
        showError(data.error || 'Analysis failed. Please try again.');
      } else if (pollCount >= maxPolls) {
        clearInterval(pollInterval);
        pollInterval = null;
        hideLoading();
        showError('Analysis is taking too long. Please try again.');
      }
    } catch (err) {
      console.error('Polling error:', err);
      // Don't stop polling on network errors, just continue
    }
  }, 2000); // Poll every 2 seconds
}

function updateLoadingMessage(data) {
  const overlay = document.getElementById('loading-overlay');
  if (!overlay) return;
  
  const loadingSub = overlay.querySelector('.loading-sub');
  const steps = overlay.querySelectorAll('.loading-steps li');
  
  if (!loadingSub) return;
  
  // Update based on status
  if (data.status === 'PROGRESS') {
    if (data.message) {
      loadingSub.textContent = data.message;
    }
    
    // Update steps based on progress
    if (data.step === 'analyzing') {
      // Activate first step
      if (steps[0]) steps[0].classList.add('active');
      if (steps[1]) steps[1].classList.remove('active');
      if (steps[2]) steps[2].classList.remove('active');
    } else if (data.step === 'saving') {
      // Activate first two steps
      if (steps[0]) steps[0].classList.add('active');
      if (steps[1]) steps[1].classList.add('active');
      if (steps[2]) steps[2].classList.remove('active');
    }
  } else if (data.status === 'PENDING') {
    loadingSub.textContent = 'Starting analysis...';
  }
}

// Helpers
async function safeJson(res) {
  const text = await res.text();
  try { return JSON.parse(text); }
  catch { return { error: text.slice(0, 300) }; } // shows HTML if server returned HTML
}

// ── HANDLE FILE UPLOAD ───────────────────────────────────────────────────
async function handleFileUpload(file) {
  if (file.size > 10 * 1024 * 1024) { 
    showError('File too large. Maximum size is 10MB.'); 
    return; 
  }
  if (!isValidDocumentType(file)) {
    showError('Unsupported file type. Please upload PDF, DOCX, DOC, TXT, RTF, or ODT files.');
    return;
  }

  showLoading();

  const formData = new FormData();
  // ✅ either key works because backend accepts both, but pick ONE for consistency:
  formData.append('contract_pdf', file);

  const csrftoken = getCookie('csrftoken') || document.querySelector('[name=csrfmiddlewaretoken]')?.value;

  try {
    const res = await fetch('/analyze-document/', {
      method: 'POST',
      credentials: 'same-origin', // ✅ send session cookie
      headers: {
        'X-CSRFToken': csrftoken,
        'Accept': 'application/json',
      },
      body: formData
    });

    const data = await safeJson(res);

    if (!res.ok) throw new Error(data.error || 'Upload failed.');

    if (data.task_id) pollTaskStatus(data.task_id);
    else if (data.redirect) window.location.href = data.redirect;
    else throw new Error('Invalid response from server');

  } catch (err) {
    hideLoading();
    showError(err.message);
  }
}

// ── SUBMIT TEXT ───────────────────────────────────────────────────────────────
async function submitText() {
  const text = document.getElementById('contract-text').value.trim();
  if (text.length < 100) { 
    showError('Please paste at least 100 characters of contract text.'); 
    return; 
  }

  showLoading();

  const csrftoken = getCookie('csrftoken') || document.querySelector('[name=csrfmiddlewaretoken]')?.value;

  try {
    const res = await fetch('/analyze-text/', {
      method: 'POST',
      credentials: 'same-origin', // ✅ send session cookie
      headers: { 
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken,
        'Accept': 'application/json',
      },
      body: JSON.stringify({ text }),
    });

    const data = await safeJson(res);

    if (!res.ok) throw new Error(data.error || 'Analysis failed.');

    if (data.task_id) pollTaskStatus(data.task_id);
    else if (data.redirect) window.location.href = data.redirect;
    else throw new Error('Invalid response from server');

  } catch (err) { 
    hideLoading(); 
    showError(err.message); 
  }
}

// ── POLL TASK STATUS ───────────────────────────────────────────────────────────
function pollTaskStatus(taskId) {
  let pollCount = 0;
  const maxPolls = 300;

  if (pollInterval) clearInterval(pollInterval);

  pollInterval = setInterval(async () => {
    pollCount++;
    try {
      const res = await fetch(`/task-status/${taskId}/`, {
        credentials: 'same-origin', // ✅ include cookie here too
        headers: { 'Accept': 'application/json' }
      });
      const data = await safeJson(res);

      updateLoadingMessage(data);

      if (data.status === 'SUCCESS') {
        clearInterval(pollInterval);
        pollInterval = null;
        showLoadingComplete();
        setTimeout(() => window.location.href = data.redirect, 800);
      } else if (data.status === 'FAILURE') {
        clearInterval(pollInterval);
        pollInterval = null;
        hideLoading();
        showError(data.error || 'Analysis failed. Please try again.');
      } else if (pollCount >= maxPolls) {
        clearInterval(pollInterval);
        pollInterval = null;
        hideLoading();
        showError('Analysis is taking too long. Please try again.');
      }
    } catch (err) {
      console.error('Polling error:', err);
    }
  }, 2000);
}

// ── LOADING ───────────────────────────────────────────────────────────────────
function showLoading() {
  hideError();
  const overlay = document.getElementById('loading-overlay');
  if (!overlay) return;
  
  // Show overlay
  overlay.style.display = 'flex';
  
  // Get all steps
  const steps = overlay.querySelectorAll('.loading-steps li');
  
  // Reset all steps (remove active class)
  steps.forEach(step => step.classList.remove('active'));
  
  // Reset spinner
  const spinner = overlay.querySelector('.spinner');
  if (spinner) {
    spinner.style.borderTopColor = '';
    spinner.style.animation = '';
    spinner.innerHTML = '';
    spinner.style.fontSize = '';
    spinner.style.display = '';
  }
  
  // Clear any existing timeouts
  if (window.loadingTimeouts) {
    window.loadingTimeouts.forEach(timeout => clearTimeout(timeout));
  }
  
  // Create new timeouts array
  window.loadingTimeouts = [];
  
  // Clear any existing poll interval
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
  
  // Set initial message
  const loadingSub = overlay.querySelector('.loading-sub');
  if (loadingSub) {
    loadingSub.textContent = 'Starting analysis...';
    loadingSub.style.color = ''; // Reset color
  }
  
  const loadingTitle = overlay.querySelector('.loading-title');
  if (loadingTitle) {
    loadingTitle.textContent = 'Analyzing your contract...';
  }
  
  // Animate steps sequentially using their data-delay attributes
  steps.forEach(step => {
    const delay = parseInt(step.dataset.delay || 0);
    const timeout = setTimeout(() => {
      step.classList.add('active');
    }, delay);
    
    window.loadingTimeouts.push(timeout);
  });
  
  // Also set a timeout to show "still working" message if analysis takes too long
  const stillWorkingTimeout = setTimeout(() => {
    const loadingTitle = overlay.querySelector('.loading-title');
    const loadingSub = overlay.querySelector('.loading-sub');
    
    if (loadingTitle && loadingSub) {
      // Check if we're still on the last step
      const lastStep = steps[steps.length - 1];
      if (lastStep && !lastStep.classList.contains('active')) {
        loadingSub.textContent = 'This is taking longer than usual...';
        loadingSub.style.color = '#FFD700';
      }
    }
  }, 15000); // Increased to 15 seconds
  
  window.loadingTimeouts.push(stillWorkingTimeout);
}

function hideLoading() {
  const overlay = document.getElementById('loading-overlay');
  if (!overlay) return;
  
  // Clear all timeouts
  if (window.loadingTimeouts) {
    window.loadingTimeouts.forEach(timeout => clearTimeout(timeout));
    window.loadingTimeouts = [];
  }
  
  // Clear poll interval
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
  
  // Reset loading messages
  const loadingTitle = overlay.querySelector('.loading-title');
  const loadingSub = overlay.querySelector('.loading-sub');
  
  if (loadingTitle) {
    loadingTitle.textContent = 'Analyzing your contract...';
  }
  if (loadingSub) {
    loadingSub.textContent = 'Our AI engine is reviewing every clause';
    loadingSub.style.color = ''; // Reset color
  }
  
  // Reset steps
  const steps = overlay.querySelectorAll('.loading-steps li');
  steps.forEach(step => step.classList.remove('active'));
  
  // Reset spinner
  const spinner = overlay.querySelector('.spinner');
  if (spinner) {
    spinner.style.borderTopColor = '';
    spinner.style.animation = '';
    spinner.innerHTML = '';
    spinner.style.fontSize = '';
    spinner.style.display = '';
  }
  
  // Hide overlay
  overlay.style.display = 'none';
}

function showLoadingComplete() {
  const overlay = document.getElementById('loading-overlay');
  if (!overlay) return;
  
  // Clear pending timeouts
  if (window.loadingTimeouts) {
    window.loadingTimeouts.forEach(timeout => clearTimeout(timeout));
  }
  
  // Clear poll interval
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
  
  // Activate all steps
  const steps = overlay.querySelectorAll('.loading-steps li');
  steps.forEach(step => step.classList.add('active'));
  
  // Update messages
  const loadingTitle = overlay.querySelector('.loading-title');
  const loadingSub = overlay.querySelector('.loading-sub');
  
  if (loadingTitle) {
    loadingTitle.textContent = 'Analysis Complete!';
  }
  if (loadingSub) {
    loadingSub.textContent = 'Redirecting to results...';
  }
  
  // Add a little checkmark animation
  const spinner = overlay.querySelector('.spinner');
  if (spinner) {
    spinner.style.borderTopColor = '#4CAF50';
    spinner.style.animation = 'none';
    spinner.innerHTML = '✓';
    spinner.style.fontSize = '2rem';
    spinner.style.display = 'flex';
    spinner.style.alignItems = 'center';
    spinner.style.justifyContent = 'center';
  }
}

// ── ERRORS ────────────────────────────────────────────────────────────────────
function showError(msg) {
  const el = document.getElementById('error-box');
  if (!el) return;
  el.textContent = `⚠️ ${msg}`;
  el.style.display = 'block';
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  
  // Auto-hide error after 8 seconds
  setTimeout(() => {
    if (el.style.display === 'block') {
      el.style.display = 'none';
    }
  }, 8000);
}

function hideError() {
  const el = document.getElementById('error-box');
  if (el) el.style.display = 'none';
}

// ── RISK CARD TOGGLE ──────────────────────────────────────────────────────────
function toggleRisk(header) {
  header.closest('.risk-card').classList.toggle('open');
}

// ── RISK REVIEW ───────────────────────────────────────────────────────────────
async function updateRisk(riskId, status, btn) {
  const card = btn.closest('.risk-card');
  const note = card.querySelector('.review-note').value;

  // Optimistic UI update
  card.querySelectorAll('.review-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const pill = card.querySelector('.status-pill');
  if (pill) { 
    pill.className = `status-pill status-${status}`; 
    pill.textContent = status.charAt(0).toUpperCase() + status.slice(1); 
  }

  const csrftoken = getCookie('csrftoken') || document.querySelector('[name=csrfmiddlewaretoken]')?.value;

  try {
    await fetch(`/risk/${riskId}/update/`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json', 
        'X-CSRFToken': csrftoken 
      },
      body: JSON.stringify({ status, note }),
    });
  } catch (err) {
    console.error('Failed to update risk:', err);
    showError('Failed to save risk status');
  }
}
function appendBubble(container, role, text) {
  const div = document.createElement('div');

  // role can be: 'user', 'assistant', 'assistant typing'
  div.className = `chat-bubble ${role}`;

  // keep it safe (no HTML injection)
  div.textContent = text;

  container.appendChild(div);

  // auto-scroll to latest
  container.scrollTop = container.scrollHeight;

  return div;
}
async function saveNote(riskId, note) {
  const card = document.getElementById(`risk-card-${riskId}`) || document.querySelector(`[id^="risk-card-"]`);
  const active = card ? card.querySelector('.review-btn.active') : null;
  const status = active ? active.textContent.trim().toLowerCase().replace('✓ ', '').replace('✔ ', '').replace('✗ ', '') : 'pending';

  const csrftoken = getCookie('csrftoken') || document.querySelector('[name=csrfmiddlewaretoken]')?.value;

  try {
    // FIXED: This should be the risk update endpoint, not chat
    await fetch(`/risk/${riskId}/update/`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json', 
        'X-CSRFToken': csrftoken 
      },
      body: JSON.stringify({ status, note }),
    });
  } catch (err) {
    console.error('Failed to save note:', err);
    showError('Failed to save note');
  }
}

// ── CHAT ──────────────────────────────────────────────────────────────────────
function chatKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
}

function askSuggestion(btn) {
  const input = document.getElementById('chat-input');
  if (input) { input.value = btn.textContent; sendChat(); }
}

async function sendChat() {
  const input   = document.getElementById('chat-input');
  const msgs    = document.getElementById('chat-messages');
  if (!input || !msgs) return;

  const message = input.value.trim();
  if (!message) return;

  // FIXED: Use CONTRACT_ID from the global variable
  const contractId = window.CONTRACT_ID;
  if (!contractId) {
    console.error('Contract ID not found');
    showError('Chat not available');
    return;
  }

  // Append user bubble
  appendBubble(msgs, 'user', message);
  input.value = '';

  // Typing indicator
  const typing = appendBubble(msgs, 'assistant typing', '...');

  const csrftoken = getCookie('csrftoken') || document.querySelector('[name=csrfmiddlewaretoken]')?.value;

  try {
    // FIXED: Use the URL from your template or construct it properly
    const url = `/chat/${contractId}/send/`;
    
    const res = await fetch(url, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json', 
        'X-CSRFToken': csrftoken 
      },
      body: JSON.stringify({ message }),
    });
    
    const data = await res.json();
    typing.remove();
    
    if (data.reply) {
      appendBubble(msgs, 'assistant', data.reply);
    } else {
      appendBubble(msgs, 'assistant', '⚠️ ' + (data.error || 'Something went wrong.'));
    }
  } catch (err) {
    console.error('Chat error:', err);
    typing.remove();
    appendBubble(msgs, 'assistant', '⚠️ Could not reach the server.');
  }
}

// ── MOBILE MENU ───────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const menuBtn = document.querySelector(".mobile-menu-btn");
  const nav = document.querySelector(".nav");

  if (!menuBtn || !nav) return;

  const openMenu = () => {
    menuBtn.classList.add("open");
    nav.classList.add("open");
    menuBtn.setAttribute("aria-expanded", "true");
    document.body.style.overflow = "hidden";
  };

  const closeMenu = () => {
    menuBtn.classList.remove("open");
    nav.classList.remove("open");
    menuBtn.setAttribute("aria-expanded", "false");
    document.body.style.overflow = "";
  };

  const toggleMenu = () => {
    if (nav.classList.contains("open")) closeMenu();
    else openMenu();
  };

  menuBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    toggleMenu();
  });

  // Close on link click (mobile)
  nav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", closeMenu);
  });

  // Close when clicking outside
  document.addEventListener("click", (e) => {
    if (!nav.contains(e.target) && !menuBtn.contains(e.target)) {
      closeMenu();
    }
  });

  // Close on ESC
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeMenu();
  });

  // Close when resizing to desktop
  window.addEventListener("resize", () => {
    if (window.innerWidth > 768) closeMenu();
  });
});

// ── CLEANUP ON PAGE UNLOAD ────────────────────────────────────────────────────
window.addEventListener('beforeunload', () => {
  if (pollInterval) {
    clearInterval(pollInterval);
  }
  if (window.loadingTimeouts) {
    window.loadingTimeouts.forEach(timeout => clearTimeout(timeout));
  }
});