const API_BASE = String(window.CODE_REVIEW_CONFIG?.apiBaseUrl || '').replace(/\/+$/, '');
let MAX_CODE_CHARS = Number(window.CODE_REVIEW_CONFIG?.maxCodeChars || 250000);
const PROJECT_LIMITS = {
  files: Number(window.CODE_REVIEW_CONFIG?.maxProjectFiles || 100),
  fileBytes: Number(window.CODE_REVIEW_CONFIG?.maxProjectFileBytes || 250000),
  totalBytes: Number(window.CODE_REVIEW_CONFIG?.maxProjectTotalBytes || 2000000),
  pathChars: Number(window.CODE_REVIEW_CONFIG?.maxProjectPathChars || 512),
  filenameChars: Number(window.CODE_REVIEW_CONFIG?.maxProjectFilenameChars || 255),
  contextChars: Number(window.CODE_REVIEW_CONFIG?.maxProjectContextChars || 50000),
  relatedFileChars: Number(window.CODE_REVIEW_CONFIG?.maxProjectRelatedFileChars || 12000),
};
const REQUEST_TIMEOUT_MS = Number(window.CODE_REVIEW_CONFIG?.requestTimeoutMs || 30000);


const state = {
  route: 'signin',
  theme: localStorage.getItem('codeReviewTheme') || 'light',
  session: JSON.parse(localStorage.getItem('codeReviewSession') || 'null'),
  reviewResult: null,
  findingWorkflows: {},
  reviews: [],
  reviewsLoaded: false,
  reviewsLoading: false,
  reviewsError: '',
  reviewSearch: '',
  reviewLanguageFilter: 'all',
  reviewStatusFilter: 'all',
  historyPage: 0,
  findingFilter: 'All',
  selectedReviewId: null,
  sidebarOpen: false,
  currentTab: 'overview',
  reviewMode: 'single',
  projectFiles: [],
  projectName: 'Code Review Project',
  projectEntryFile: '',
  currentWorkspacePath: null,
  settingsSection: 'General',
  preferences: readSavedPreferences(),
};

const icons = {
  dashboard: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 13.5h7V4H4zm9 6.5h7V11h-7zm0-16v6h7V4zm-9 9h7v7H4z" fill="currentColor"/></svg>',
  review: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4.75A2.75 2.75 0 0 1 7.75 2h8.5A2.75 2.75 0 0 1 19 4.75v14.5A2.75 2.75 0 0 1 16.25 22h-8.5A2.75 2.75 0 0 1 5 19.25zm2.5 1.5v12.5h9V6.25zm2 2.5h5v1.5h-5zm0 3h5v1.5h-5zm0 3h3.5v1.5H9.5z" fill="currentColor"/></svg>',
  history: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13 2a9 9 0 1 1-6.6 15.4l.7.7-1.4 1.4L3.6 17l1.4-1.4.7.7A10.97 10.97 0 1 0 13 2zm1 5h-1.5v5.2l4.4 2.7 0.8-1.3-3.7-2.2V7z" fill="currentColor"/></svg>',
  bookmark: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6.5 3.5A2.5 2.5 0 0 1 9 1h6a2.5 2.5 0 0 1 2.5 2.5V22l-5.5-4-5.5 4z" fill="currentColor"/></svg>',
  settings: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19.1 12.9a7.2 7.2 0 0 0 .08-1l2.1-1.6-2-3.4-2.5 1a7 7 0 0 0-1.7-1L14.5 3h-5l-.6 2.9a6.7 6.7 0 0 0-1.7 1l-2.5-1-2 3.4 2.1 1.6a7.2 7.2 0 0 0 0 2l-2.1 1.6 2 3.4 2.5-1a7 7 0 0 0 1.7 1l.6 2.9h5l.6-2.9a6.7 6.7 0 0 0 1.7-1l2.5 1 2-3.4zm-7.1 2.1a3.8 3.8 0 1 1 0-7.6 3.8 3.8 0 0 1 0 7.6z" fill="currentColor"/></svg>',
  help: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M11 18h2v2h-2zm1-16a9 9 0 1 1 0 18 9 9 0 0 1 0-18zm0 15.5a1.25 1.25 0 1 0 0 2.5 1.25 1.25 0 0 0 0-2.5zm1.9-12.3-1 6.9h-1.8l-.7-4.1A4.3 4.3 0 0 1 12.8 7a2 2 0 0 0-1.8-1A2.2 2.2 0 0 0 8.8 8.2l-1.7-.9A4 4 0 1 1 16.4 9.2z" fill="currentColor"/></svg>',
  plus: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6z" fill="currentColor"/></svg>',
  search: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10.5 3a7.5 7.5 0 1 1 0 15 7.5 7.5 0 0 1 0-15zm9.5 19.3-5.3-5.3 1.4-1.4 5.3 5.3z" fill="currentColor"/></svg>',
  bell: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a5 5 0 0 1 5 5v4.1l1.7 3.4H5.3l1.7-3.4V8a5 5 0 0 1 5-5zm0 18a2.5 2.5 0 0 1-2.45-2h4.9A2.5 2.5 0 0 1 12 21z" fill="currentColor"/></svg>',
  moon: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.4 15.4A8.7 8.7 0 0 1 8.6 3.6a8.8 8.8 0 1 0 11.8 11.8z" fill="currentColor"/></svg>',
  sun: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2.5h.9l.4 2.2 1.8-.9 1.2 1.2-.9 1.8 2.2.4v.9l-2.2.4.9 1.8-1.2 1.2-1.8-.9-.4 2.2H12l-.4-2.2-1.8.9-1.2-1.2.9-1.8-2.2-.4v-.9l2.2-.4-.9-1.8 1.2-1.2 1.8.9.4-2.2zm0 6a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7z" fill="currentColor"/></svg>',
  upload: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.5 5.5 10l1.4 1.4L11 7.2V16h2V7.2l4.1 4.2 1.4-1.4L12 3.5zm-7 14.5h14v2H5z" fill="currentColor"/></svg>',
  copy: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 7.5A2.5 2.5 0 0 1 9.5 5H18a2 2 0 0 1 2 2v8.5A2.5 2.5 0 0 1 17.5 18H9.5A2.5 2.5 0 0 1 7 15.5zm-2 1.5A3 3 0 0 0 2 12v6a3 3 0 0 0 3 3h7a3 3 0 0 0 3-3v-6a3 3 0 0 0-3-3H5z" fill="currentColor"/></svg>',
  chevron: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 10l5 5 5-5z" fill="currentColor"/></svg>',
  code: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8.2 7.9 3.6 12l4.6 4.1-1.3 1.5L1 12l5.9-5.6zm7.6 8.2L20.4 12l-4.6-4.1 1.3-1.5L23 12l-5.9 5.6zM13.5 4l-2.8 16h2.6L16.1 4z" fill="currentColor"/></svg>',
  security: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2 4 5v6c0 5.1 3.4 9.6 8 11 4.6-1.4 8-5.9 8-11V5zm0 3.2 5 1.9v3.9c0 3.6-2.1 6.9-5 8.2-2.9-1.3-5-4.6-5-8.2V7.1z" fill="currentColor"/></svg>',
  performance: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12h4l2-6 4 12 2-6h6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  menu: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
  shield: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2 4.5 5v5.8c0 4.9 3.2 9.1 7.5 10.5 4.3-1.4 7.5-5.6 7.5-10.5V5zm0 3 4.5 1.8v4c0 3.5-1.8 6.6-4.5 7.9-2.7-1.3-4.5-4.4-4.5-7.9v-4z" fill="currentColor"/></svg>'
};

const navigation = [
  { id: 'dashboard', label: 'Overview', icon: icons.dashboard },
  { id: 'new-review', label: 'New Review', icon: icons.review },
  { id: 'history', label: 'Reviews', icon: icons.history },
  { id: 'workspace', label: 'Code Workspace', icon: icons.code },
  { id: 'findings', label: 'Findings', icon: icons.code },
  { id: 'agents', label: 'Agents', icon: icons.settings },
  { id: 'test-generator', label: 'Test Generator', icon: icons.plus },
  { id: 'reports', label: 'Reports', icon: icons.review },
  { id: 'security', label: 'Security', icon: icons.help },
  { id: 'performance', label: 'Performance', icon: icons.code },
  { id: 'fixes', label: 'AI Fixes', icon: icons.copy },
  { divider: true },
  { id: 'github', label: 'GitHub', icon: icons.code },
  { id: 'help', label: 'Documentation', icon: icons.help },
  { id: 'settings', label: 'Settings', icon: icons.settings },
];

const languageOptions = [
  'Auto Detect', 'Python', 'JavaScript', 'TypeScript', 'Java', 'C', 'C++', 'C#', 'Go', 'Rust', 'PHP', 'Ruby', 'Kotlin', 'Swift', 'SQL', 'HTML', 'CSS', 'Shell', 'PowerShell'
];

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function normalizeReviewData(data) {
  if (!data || typeof data !== 'object') {
    return {
      summary: { overall_risk_level: 'LOW', files_reviewed: [], lines_reviewed: 0 },
      language: { language: 'Unknown', confidence: 0 },
      bugs: [],
      security: [],
      performance: [],
      code_quality: [],
      tests: [],
      fixes: [],
      static_analysis: {},
    };
  }

  const projectFindings = Array.isArray(data.findings) ? data.findings : [];
  const findings = Array.isArray(data.findings) ? {} : (data.findings || {});
  const summary = data.summary || {};
  const projectFindingsFor = (agentName) => projectFindings.filter((item) => item.agent === agentName);

  return {
    ...data,
    summary: data.summary || {
      overall_risk_level: projectFindings.some((item) => item.severity === 'CRITICAL') ? 'CRITICAL' :
        projectFindings.some((item) => item.severity === 'HIGH') ? 'HIGH' :
          projectFindings.some((item) => item.severity === 'MEDIUM') ? 'MEDIUM' : 'LOW',
      files_reviewed: (data.file_reviews || []).map((item) => item.path),
      lines_reviewed: 0,
      language: (data.languages || []).map((item) => item.language).join(', '),
    },
    language: data.language || { language: (data.languages || []).map((item) => item.language).join(', ') || 'Unknown', confidence: 0 },
    bugs: Array.isArray(data.bugs) ? data.bugs : (Array.isArray(findings.bugs) ? findings.bugs : projectFindingsFor('Bug Agent')),
    security: Array.isArray(data.security) ? data.security : (Array.isArray(findings.security) ? findings.security : projectFindingsFor('Security Agent')),
    performance: Array.isArray(data.performance) ? data.performance : (Array.isArray(findings.performance) ? findings.performance : projectFindingsFor('Performance Agent')),
    code_quality: Array.isArray(data.code_quality) ? data.code_quality : (Array.isArray(findings.code_quality) ? findings.code_quality : projectFindingsFor('Code Quality Agent')),
    tests: Array.isArray(data.tests) ? data.tests : (Array.isArray(findings.tests) ? findings.tests : []),
    fixes: Array.isArray(data.fixes) ? data.fixes : (Array.isArray(findings.fixes) ? findings.fixes : []),
    static_analysis: data.static_analysis || {},
  };
}

async function requestJson(path, options = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const fetchOptions = {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
    signal: controller.signal,
  };

  try {
    const response = await fetch(`${API_BASE}${path}`, fetchOptions);
    let payload;
    try {
      payload = await response.json();
    } catch {
      throw new Error('The review service returned an invalid response. Please try again.');
    }

    if (!response.ok || payload?.success !== true || !Object.hasOwn(payload, 'data')) {
      const message = payload?.error?.message || (response.status === 413
        ? 'The submitted code is too large.'
        : 'The review service could not complete the request.');
      throw new Error(message);
    }
    return payload.data;
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('The request timed out. Please try again with a smaller review.');
    }
    if (error instanceof TypeError) {
      throw new Error('Unable to connect to the review service. Check that the backend is running.');
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

async function loadPersistedReviews() {
  const result = await requestJson('/reviews?limit=100');
  state.reviews = Array.isArray(result?.reviews) ? result.reviews : [];
  state.reviewsError = '';
  state.reviewsLoaded = true;
}

async function refreshPersistedReviews() {
  try {
    await loadPersistedReviews();
    renderApp();
  } catch {
    state.reviewsError = 'Unable to load persisted reviews. Check the backend connection.';
    state.reviewsLoaded = true;
  }
}

requestJson('/config').then((config) => {
  const limits = config?.limits;
  if (!limits) return;
  MAX_CODE_CHARS = Number(limits.max_code_chars || MAX_CODE_CHARS);
  PROJECT_LIMITS.files = Number(limits.max_project_files || PROJECT_LIMITS.files);
  PROJECT_LIMITS.fileBytes = Number(limits.max_project_file_bytes || PROJECT_LIMITS.fileBytes);
  PROJECT_LIMITS.totalBytes = Number(limits.max_project_total_bytes || PROJECT_LIMITS.totalBytes);
  PROJECT_LIMITS.pathChars = Number(limits.max_project_path_chars || PROJECT_LIMITS.pathChars);
  PROJECT_LIMITS.filenameChars = Number(limits.max_project_filename_chars || PROJECT_LIMITS.filenameChars);
  PROJECT_LIMITS.contextChars = Number(limits.max_project_context_chars || PROJECT_LIMITS.contextChars);
  PROJECT_LIMITS.relatedFileChars = Number(limits.max_project_related_file_chars || PROJECT_LIMITS.relatedFileChars);
}).catch(() => {});

function currentUser() {
  return state.session || { name: 'Charitha', email: 'demo@codereviewagent.dev' };
}

function saveSession() {
  localStorage.setItem('codeReviewSession', JSON.stringify(state.session));
}

function readSavedPreferences() {
  try {
    return JSON.parse(localStorage.getItem('codeReviewPreferences') || '{}');
  } catch {
    return {};
  }
}

function resolveThemeValue(themePreference) {
  if (themePreference === 'system') {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  return themePreference === 'dark' ? 'dark' : 'light';
}

function setTheme(theme) {
  state.theme = theme;
  localStorage.setItem('codeReviewTheme', theme);
  document.documentElement.setAttribute('data-theme', resolveThemeValue(theme));
}

function toast(message, type = 'success') {
  const wrapper = document.getElementById('toast-stack') || document.body.appendChild(Object.assign(document.createElement('div'), { id: 'toast-stack', className: 'toast-stack' }));
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = message;
  wrapper.appendChild(el);
  setTimeout(() => el.remove(), 2600);
}

function renderAuthView() {
  const app = document.getElementById('app');
  app.innerHTML = `
    <div class="auth-page">
      <section class="auth-visual">
        <div class="hero-badge">AI DEVELOPER TEAM</div>
        <h1 class="hero-title">AI Code Review,<br>Powered by a Team<br>of <span>Agents.</span></h1>
        <p class="hero-copy">One codebase. Multiple specialists. One structured review.</p>
        <div class="hero-actions"><button type="button" class="button button-primary" id="start-free-review">Start Free Review ${icons.chevron}</button><button type="button" class="button button-secondary" id="view-demo">View Demo</button></div>
        <div class="architecture-diagram">
          <div class="arch-step arch-source"><span>${icons.code}</span><div><strong>Your Code</strong><small>Files and project context</small></div></div>
          <div class="arch-connector"></div>
          <div class="arch-step arch-orchestrator"><span>${icons.settings}</span><div><strong>Orchestrator Agent</strong><small>Coordinates review passes</small></div></div>
          <div class="arch-connector"></div>
          <div class="arch-agent-grid"><div class="arch-step"><span class="agent-mark bug">B</span><strong>Bug Agent</strong></div><div class="arch-step"><span class="agent-mark sec">S</span><strong>Security Agent</strong></div><div class="arch-step"><span class="agent-mark perf">P</span><strong>Performance</strong></div><div class="arch-step"><span class="agent-mark quality">Q</span><strong>Code Quality</strong></div></div>
          <div class="arch-connector"></div>
          <div class="arch-step arch-final"><span>${icons.review}</span><div><strong>Test Agent</strong><small>Provider-backed test suggestions</small></div><span class="arch-report">Final Report</span></div>
        </div>
        <div class="feature-strip"><div><strong>Multi-Agent Analysis</strong><small>Specialist review passes</small></div><div><strong>Actionable Fixes</strong><small>Proposals stay reviewable</small></div><div><strong>Automated Tests</strong><small>Provider required</small></div><div><strong>Security Analysis</strong><small>Evidence-based checks</small></div><div><strong>Performance Analysis</strong><small>Pattern-based checks</small></div><div><strong>Final Reports</strong><small>Structured findings</small></div></div>
      </section>

      <section class="auth-panel">
        <div class="auth-card">
          <div class="auth-logo">
            <div class="brand-mark">C</div>
            <div class="brand-copy">
              <h3>CodeReview Agent</h3>
              <span>AI Developer Team</span>
            </div>
          </div>

          <div class="auth-header">
            <h2>Welcome back</h2>
            <p>Open your CodeReview workspace.</p>
          </div>

          <form id="signin-form" class="form-grid" novalidate>
            <div class="field">
              <label for="signin-email">Email</label>
              <input id="signin-email" type="email" name="email" placeholder="you@company.com" required />
            </div>
            <div class="field">
              <label for="signin-password">Password</label>
              <input id="signin-password" type="password" name="password" placeholder="••••••••" required />
            </div>
            <div class="row">
              <label class="checkbox"><input type="checkbox" checked /> Remember me</label>
              <button type="button" class="inline-link button-ghost" data-route="forgot">Forgot password?</button>
            </div>
            <div class="auth-actions">
              <button type="submit" class="button button-primary" style="width:100%;">Open Workspace</button>
            </div>
          </form>

          <div class="auth-footer">
            Don’t have an account? <button type="button" class="inline-link button-ghost" data-route="signup">Create account</button>
          </div>
        </div>
      </section>
    </div>
  `;

  bindAuthEventHandlers();
  document.getElementById('start-free-review')?.addEventListener('click', () => document.getElementById('signin-email')?.focus());
  document.getElementById('view-demo')?.addEventListener('click', () => {
    state.session = { name: 'Charitha', email: 'demo@codereviewagent.dev' };
    saveSession();
    state.route = 'dashboard';
    renderApp();
  });
}

function renderSignupView() {
  const app = document.getElementById('app');
  app.innerHTML = `
    <div class="auth-page">
      <section class="auth-visual">
        <div class="hero-badge">AI DEVELOPER TEAM</div>
        <h1 class="hero-title">CodeReview Agent</h1>
        <p class="hero-copy">Build faster by turning code reviews into a structured, developer-friendly workflow across bug detection, security checks, performance analysis, tests, and fixes.</p>
        <ul class="hero-features">
          <li>Safe demo-only auth</li>
          <li>Reusable review workflows</li>
          <li>Product-ready dashboard</li>
        </ul>
      </section>

      <section class="auth-panel">
        <div class="auth-card">
          <div class="auth-logo">
            <div class="brand-mark">C</div>
            <div class="brand-copy">
              <h3>CodeReview Agent</h3>
              <span>AI Developer Team</span>
            </div>
          </div>

          <div class="auth-header">
            <h2>Create account</h2>
            <p>Set up your workspace and start reviewing code faster.</p>
          </div>

          <form id="signup-form" class="form-grid" novalidate>
            <div class="field">
              <label for="signup-name">Full name</label>
              <input id="signup-name" type="text" placeholder="Ada Lovelace" required />
            </div>
            <div class="field">
              <label for="signup-email">Email</label>
              <input id="signup-email" type="email" placeholder="you@company.com" required />
            </div>
            <div class="field">
              <label for="signup-password">Password</label>
              <input id="signup-password" type="password" placeholder="Create a password" required />
            </div>
            <div class="field">
              <label for="signup-confirm">Confirm password</label>
              <input id="signup-confirm" type="password" placeholder="Confirm your password" required />
            </div>
            <div class="auth-actions">
              <button type="submit" class="button button-primary" style="width:100%;">Create account</button>
            </div>
          </form>

          <div class="auth-footer">
            Already have an account? <button type="button" class="inline-link button-ghost" data-route="signin">Sign in</button>
          </div>
        </div>
      </section>
    </div>
  `;

  bindAuthEventHandlers();
}

function renderForgotView() {
  const app = document.getElementById('app');
  app.innerHTML = `
    <div class="auth-page">
      <section class="auth-visual">
        <div class="hero-badge">RECOVER ACCESS</div>
        <h1 class="hero-title">Reset your password</h1>
        <p class="hero-copy">This is a demo flow for the frontend prototype. Replace it with a real backend reset endpoint when authentication is added.</p>
      </section>
      <section class="auth-panel">
        <div class="auth-card">
          <div class="auth-header">
            <h2>Forgot password</h2>
            <p>Enter your email to receive a reset link.</p>
          </div>
          <form id="forgot-form" class="form-grid">
            <div class="field">
              <label for="forgot-email">Email</label>
              <input id="forgot-email" type="email" placeholder="you@company.com" required />
            </div>
            <div class="auth-actions">
              <button type="submit" class="button button-primary" style="width:100%;">Send reset link</button>
            </div>
          </form>
          <div class="auth-footer">
            <button type="button" class="inline-link button-ghost" data-route="signin">Back to sign in</button>
          </div>
        </div>
      </section>
    </div>
  `;

  bindAuthEventHandlers();
}

function renderShell() {
  const app = document.getElementById('app');
  const user = currentUser();

  app.innerHTML = `
    <div class="app-shell">
      <button type="button" class="sidebar-scrim ${state.sidebarOpen ? 'visible' : ''}" aria-label="Close navigation" data-action="close-sidebar"></button>
      <aside class="sidebar ${state.sidebarOpen ? 'open' : ''}">
        <div>
          <div class="brand">
            <div class="brand-mark" aria-hidden="true">${icons.shield}</div>
            <div class="brand-copy">
              <h3>CodeReview Agent</h3>
              <span>AI Developer Team</span>
            </div>
          </div>

          <div class="nav-section">
            <div class="nav-label">Workspace</div>
            <ul class="nav-list">
              ${navigation.map((item) => item.divider ? '<li class="nav-divider" aria-hidden="true"></li>' : `
                <li>
                  <button type="button" class="nav-item ${state.route === item.id ? 'active' : ''}" data-route="${item.id}">
                    <span class="nav-icon">${item.icon}</span>
                    ${item.label}
                  </button>
                </li>
              `).join('')}
            </ul>
          </div>
        </div>

        <div class="sidebar-footer">
          <div class="user-card">
            <div class="user-meta">
              <div class="avatar">${escapeHtml(user.name || 'DU').split(' ').map((part) => part[0]).slice(0, 2).join('').toUpperCase()}</div>
              <div>
                <h4>${escapeHtml(user.name || 'Demo User')}</h4>
                <span>${escapeHtml(user.email || 'demo@codereviewagent.dev')}</span>
              </div>
            </div>
            <button type="button" class="button-ghost" data-action="logout" style="padding:8px 10px;">Logout</button>
          </div>
        </div>
      </aside>

      <main class="main-content">
        <header class="header">
          <button type="button" class="icon-button sidebar-toggle" aria-label="Open navigation" data-action="open-sidebar">${icons.menu}</button>
          <div class="page-title">
            <h1>${pageTitleForRoute(state.route)}</h1>
            <p>${pageSubtitleForRoute(state.route)}</p>
          </div>

          <div class="header-actions">
            <div class="search-box" aria-label="Search reviews">
              ${icons.search}
              <input id="global-review-search" type="search" placeholder="Search projects, reviews, or files..." aria-label="Search projects, reviews, or files" value="${escapeHtml(state.reviewSearch)}" />
            </div>
            <button type="button" class="icon-button" aria-label="Notifications">${icons.bell}</button>
            <button type="button" id="theme-toggle" class="icon-button" aria-label="Toggle theme">${state.theme === 'dark' ? icons.sun : icons.moon}</button>
            <div class="profile-chip" tabindex="0" aria-label="User profile menu">
              <div class="avatar small">${escapeHtml(user.name || 'DU').split(' ').map((part) => part[0]).slice(0, 2).join('').toUpperCase()}</div>
              <span>${escapeHtml(user.name || 'Demo User')}</span>
              ${icons.chevron}
            </div>
          </div>
        </header>

        <div class="content-inner">
          ${renderRouteContent()}
        </div>
      </main>
    </div>
  `;

  bindShellEvents();
}

function pageTitleForRoute(route) {
  switch (route) {
    case 'dashboard': return 'Overview';
    case 'new-review': return 'Start a New Review';
    case 'workspace': return 'Code Workspace';
    case 'history': return 'Review History';
    case 'findings': return 'Findings';
    case 'agents': return 'Agent Control Center';
    case 'test-generator': return 'AI Test Generator';
    case 'reports': return 'Final Report';
    case 'security': return 'Security Center';
    case 'performance': return 'Performance';
    case 'fixes': return 'AI Fix Suggestions';
    case 'github': return 'GitHub Integration';
    case 'settings': return 'Settings';
    case 'help': return 'Documentation';
    default: return 'Overview';
  }
}

function pageSubtitleForRoute(route) {
  switch (route) {
    case 'dashboard': return 'Here is an overview of your code quality.';
    case 'new-review': return 'Choose how to provide code and configure your review.';
    case 'workspace': return 'Inspect the selected project files and run a review.';
    case 'history': return 'View and manage your saved code reviews.';
    case 'findings': return 'Review the issues returned by your selected code review.';
    case 'agents': return 'Inspect the analysis capabilities and current review results.';
    case 'test-generator': return 'Generate a test for a finding after a fix proposal is available.';
    case 'reports': return 'Review the persisted summary and findings from a code review.';
    case 'security': return 'Inspect security findings returned by the selected review.';
    case 'performance': return 'Inspect performance findings returned by the selected review.';
    case 'fixes': return 'Review proposed changes without modifying submitted source.';
    case 'github': return 'GitHub integration is not connected.';
    case 'settings': return 'Customize your workspace and review preferences.';
    case 'help': return 'Documentation for the review workflow and analysis limits.';
    default: return 'Here is an overview of your code quality.';
  }
}

function renderRouteContent() {
  switch (state.route) {
    case 'dashboard': return renderDashboard();
    case 'new-review': return renderReviewPage();
    case 'workspace': return renderWorkspacePage();
    case 'history': return renderHistoryPage();
    case 'findings': return renderFindingsPage();
    case 'agents': return renderAgentsPage();
    case 'test-generator': return renderTestGeneratorPage();
    case 'reports': return renderReportsPage();
    case 'security': return renderCategoryPage('Security', 'security');
    case 'performance': return renderCategoryPage('Performance', 'performance');
    case 'fixes': return renderFixesPage();
    case 'github': return renderUnavailablePage('GitHub integration is not connected to this backend.');
    case 'settings': return renderSettingsPage();
    case 'help': return renderHelpPage();
    default: return renderDashboard();
  }
}

function renderDashboard() {
  const reviews = state.reviews;
  const totals = reviews.reduce((result, review) => {
    for (const key of ['bugs', 'security', 'performance', 'code_quality']) {
      result[key] += Number(review.finding_counts?.[key] || 0);
    }
    result.tests += Number(review.tests_count || 0);
    result.critical += Number(review.severity_counts?.critical || 0);
    return result;
  }, { bugs: 0, security: 0, performance: 0, code_quality: 0, tests: 0, critical: 0 });
  const totalFindings = totals.bugs + totals.security + totals.performance + totals.code_quality;
  const latest = reviews[0];
  const metrics = [
    ['Reviews Completed', reviews.length, icons.history, 'teal'],
    ['Critical Issues', totals.critical, icons.security, 'red'],
    ['Bugs Found', totals.bugs, icons.code, 'orange'],
    ['Security Issues', totals.security, icons.security, 'purple'],
    ['Performance Issues', totals.performance, icons.performance, 'blue'],
    ['Tests Generated', totals.tests, icons.review, 'green'],
  ];
  const healthBars = [
    ['Security', totals.security, 'teal'],
    ['Performance', totals.performance, 'orange'],
    ['Maintainability', totals.code_quality, 'blue'],
  ];

  return `
    <div class="dashboard-page">
      <section class="welcome-row">
        <div><div class="eyebrow">AI DEVELOPER TEAM</div><h2>Good evening, ${escapeHtml(currentUser().name || 'Charitha')} <span class="greeting-spark">*</span></h2><p>Here's an overview of your code quality.</p></div>
        <button type="button" class="button button-primary" data-route="new-review">${icons.plus} New Review</button>
      </section>
      <section class="metric-grid">
        ${metrics.map(([label, value, icon, tone]) => `<article class="metric-card dashboard-metric"><div class="metric-card-head"><span class="metric-icon ${tone}">${icon}</span><span class="metric-context">Saved reviews</span></div><strong>${escapeHtml(String(value))}</strong><span class="metric-label">${escapeHtml(label)}</span></article>`).join('')}
      </section>
      <div class="dashboard-split">
        <section class="panel health-panel">
          <div class="panel-heading"><div><h3>Code Health</h3><p>Finding distribution from persisted reviews</p></div><span class="score-unavailable">No overall score</span></div>
          <div class="health-content"><div class="health-summary"><strong>${totalFindings}</strong><span>findings</span><small>${reviews.length} saved review${reviews.length === 1 ? '' : 's'}</small></div><div class="health-bars">
            ${healthBars.map(([label, value, tone]) => `<div class="health-bar-row"><div><span>${label}</span><strong>${value}</strong></div><div class="progress-track"><span class="progress-fill ${tone}" style="width:${totalFindings ? Math.round(value / totalFindings * 100) : 0}%"></span></div></div>`).join('')}
          </div></div>
        </section>
        <section class="panel activity-panel">
          <div class="panel-heading"><div><h3>Recent Agent Activity</h3><p>Persisted review activity</p></div><span class="live-indicator"><i></i> Activity</span></div>
          ${latest ? `<div class="activity-entry"><span class="activity-dot teal"></span><div><strong>Review completed</strong><p>${escapeHtml(latest.project_name)} · ${escapeHtml(latest.language)}</p></div><time>${escapeHtml(formatReviewDate(latest.created_at))}</time></div><div class="activity-entry"><span class="activity-dot ${riskClass(latest.risk_level)}"></span><div><strong>${escapeHtml(String(latest.finding_count))} findings recorded</strong><p>Risk level: ${escapeHtml(latest.risk_level)}</p></div><time>${escapeHtml(`${latest.file_count} files`)}</time></div><div class="activity-note">Live per-agent event streaming is not available.</div>` : '<div class="panel-empty">No completed review activity yet.</div>'}
        </section>
      </div>
      <section class="panel reviews-panel">
        <div class="panel-heading"><div><h3>Recent Reviews</h3><p>Saved in the review database</p></div><button type="button" class="button button-secondary" data-route="history">View all</button></div>
        <div class="table-wrap">${reviews.length ? `<table class="data-table"><thead><tr><th>Project</th><th>Language</th><th>Score</th><th>Issues</th><th>Date</th><th>Status</th></tr></thead><tbody>${reviews.slice(0, 5).map((review) => `<tr><td><button type="button" class="table-link" data-action="open-saved-review" data-review-id="${escapeHtml(review.review_id)}">${escapeHtml(review.project_name)}</button><small>${escapeHtml(String(review.file_count))} files</small></td><td>${escapeHtml(review.language)}</td><td><span class="score-plain">Not scored</span></td><td>${escapeHtml(String(review.finding_count))}</td><td>${escapeHtml(formatReviewDate(review.created_at))}</td><td><span class="status-pill">${escapeHtml(review.status)}</span></td></tr>`).join('')}</tbody></table>` : '<div class="panel-empty">No saved reviews yet. Start a review to see results here.</div>'}</div>
      </section>
      <section class="capability-strip"><div><span class="capability-check">✓</span><strong>Multi-agent heuristics</strong><small>Bug, security, performance, quality</small></div><div><span class="capability-check">✓</span><strong>Project analysis</strong><small>Files, manifests, import relationships</small></div><div><span class="capability-neutral">i</span><strong>AI analysis</strong><small>Requires a configured provider</small></div></section>
    </div>
  `;
}

function formatReviewDate(value) {
  if (!value) return 'Date unavailable';
  const date = new Date(`${value.replace(' ', 'T')}Z`);
  return Number.isNaN(date.valueOf()) ? value : new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(date);
}

function renderReviewPage() {
 const stateCode = state.reviewResult ? (state.reviewResult.code || '') : '';
  const isProjectMode = state.reviewMode === 'project';
  const selectedProjectFile = state.projectFiles.find((file) => file.path === state.currentWorkspacePath) || state.projectFiles[0];

  return `
    <div class="review-page">
      <div class="review-mode-tabs" role="radiogroup" aria-label="Review input mode">
        <label class="mode-tab ${isProjectMode ? 'active' : ''}"><input type="radio" name="review-mode" value="project" ${isProjectMode ? 'checked' : ''}><span>${icons.upload}</span><strong>Upload Project</strong><small>Review a folder of files</small></label>
        <label class="mode-tab ${isProjectMode ? '' : 'active'}"><input type="radio" name="review-mode" value="single" ${isProjectMode ? '' : 'checked'}><span>${icons.code}</span><strong>Paste Code</strong><small>Review a single file</small></label>
        <div class="mode-tab disabled" aria-disabled="true"><span>${icons.github || icons.code}</span><strong>GitHub Repository</strong><small>Integration not connected</small></div>
      </div>
      <div class="review-shell">
        <section class="panel editor-card">
          ${isProjectMode ? `
            <div class="project-review-fields">
              <label class="field"><span>Project name</span><input id="project-name-input" class="input" type="text" maxlength="100" value="${escapeHtml(state.projectName)}"></label>
              <label class="field"><span>Entry file</span><select id="project-entry-input" class="select"><option value="">Auto detect</option>${state.projectFiles.map((file) => `<option value="${escapeHtml(file.path)}" ${state.projectEntryFile === file.path ? 'selected' : ''}>${escapeHtml(file.path)}</option>`).join('')}</select></label>
            </div>
            <label class="upload-zone" for="project-upload-input">
              <span class="upload-icon">${icons.upload}</span><strong>Drag and drop your files here</strong><span>or <b>Browse Files</b></span><small>Folders or individual files · up to ${PROJECT_LIMITS.files} files</small>
              <input id="project-upload-input" type="file" multiple webkitdirectory directory hidden>
            </label>
            ${state.projectFiles.length ? `<div class="workspace-panel"><aside class="workspace-tree"><strong>Project</strong>${state.projectFiles.map((file) => `<button type="button" class="tree-file ${file.path === selectedProjectFile?.path ? 'active' : ''}" data-workspace-file="${escapeHtml(file.path)}" style="--tree-depth:${Math.max(0, file.path.split('/').length - 1)}"><span>${icons.code}</span>${escapeHtml(file.path.split('/').pop())}</button>`).join('')}</aside><div class="workspace-editor"><div class="workspace-editor-head"><strong>${escapeHtml(selectedProjectFile?.path || '')}</strong><span>${escapeHtml((selectedProjectFile?.path.split('.').pop() || 'text').toUpperCase())}</span></div><textarea class="editor" readonly spellcheck="false">${escapeHtml(selectedProjectFile?.content || '')}</textarea><div class="editor-status"><span>Read only</span><span>UTF-8</span><span>${escapeHtml(selectedProjectFile?.path.split('.').pop() || 'text')}</span></div></div></div>` : '<div class="project-file-list"><div class="panel-empty">Select a folder or files to build the project workspace.</div></div>'}
            <button type="button" class="button button-ghost" id="clear-project-btn">Clear project files</button>
          ` : `
            <div class="editor-toolbar"><div class="file-context"><span class="language-dot"></span><strong>Code Editor</strong></div><div class="toolbar-group"><label class="button button-secondary" for="file-upload-input">${icons.upload} Browse File</label><input id="file-upload-input" type="file" hidden><button type="button" class="button button-ghost" id="clear-editor-btn">Clear</button></div></div>
            <div class="editor-meta"><select id="language-select" class="select" aria-label="Select language">${languageOptions.map((value) => `<option value="${escapeHtml(value)}" ${value === 'Auto Detect' ? 'selected' : ''}>${escapeHtml(value)}</option>`).join('')}</select><input id="filename-input" class="input" type="text" value="example.py" aria-label="Filename"></div>
            <textarea id="code-editor" class="editor" spellcheck="false">${escapeHtml(stateCode)}</textarea>
            <div class="editor-status"><span>Ln 1, Col 1</span><span>Spaces: 4</span><span>UTF-8</span><span>Auto Detect</span></div>
          `}
        </section>
        <aside class="panel review-config">
          <div class="panel-heading"><div><h3>Review Configuration</h3><p>Choose analysis depth and agents</p></div></div>
          <label class="field"><span>Review depth</span><select id="review-depth" class="select"><option>Quick</option><option selected>Standard</option><option>Deep</option></select></label>
          <fieldset class="agent-options"><legend>Select agents</legend><label><input type="checkbox" checked disabled> Bug Detection</label><label><input type="checkbox" checked disabled> Security Analysis</label><label><input type="checkbox" checked disabled> Performance Analysis</label><label><input type="checkbox" checked disabled> Code Quality</label><label><input type="checkbox" disabled> Test Generation <small>Provider required</small></label></fieldset>
          <button type="button" class="button button-primary start-review-button" id="review-code-btn">Start AI Review <span>→</span></button>
          <p class="config-note">Submitted source is analyzed as data and is never executed.</p>
        </aside>
      </div>
      <section class="panel result-panel">
        <div class="result-toolbar"><div class="result-tabs" role="tablist" aria-label="Review results">${['overview','bugs','security','performance','code_quality','tests','fixes','report'].map((tab) => `<button type="button" class="tab ${state.currentTab === tab ? 'active' : ''}" data-tab="${tab}">${tabLabel(tab)}</button>`).join('')}</div><button type="button" class="button button-secondary" id="detect-language-btn" ${isProjectMode ? 'hidden' : ''}>Detect Language</button></div>
        <div class="results-body" id="review-results-body">${renderActiveResultPanel()}</div>
      </section>
    </div>
  `;
}

function tabLabel(tab) {
  const labels = {
    overview: 'Overview',
    bugs: 'Bugs',
    security: 'Security',
    performance: 'Performance',
    code_quality: 'Code Quality',
    tests: 'Tests',
    fixes: 'Fixes',
    report: 'Final Report'
  };
  return labels[tab] || 'Overview';
}

function renderHistoryPage() {
  const reviews = state.reviews.filter((review) => {
    const query = state.reviewSearch.trim().toLowerCase();
    const matchesQuery = !query || `${review.project_name} ${review.language} ${review.review_id}`.toLowerCase().includes(query);
    const matchesLanguage = state.reviewLanguageFilter === 'all' || review.language === state.reviewLanguageFilter;
    const matchesStatus = state.reviewStatusFilter === 'all' || review.status.toLowerCase() === state.reviewStatusFilter;
    return matchesQuery && matchesLanguage && matchesStatus;
  });
  const pageSize = 10;
  const pageCount = Math.max(1, Math.ceil(reviews.length / pageSize));
  state.historyPage = Math.min(state.historyPage, pageCount - 1);
  const pageReviews = reviews.slice(state.historyPage * pageSize, (state.historyPage + 1) * pageSize);
  return `
    <div class="panel reviews-panel">
      <div class="table-toolbar"><div class="filter-row"><input id="history-search" class="input" type="search" placeholder="Search projects, reviews, or files..." value="${escapeHtml(state.reviewSearch)}"><select id="history-language-filter" class="select" aria-label="Filter by language"><option value="all">All Languages</option>${[...new Set(state.reviews.map((item) => item.language))].map((language) => `<option value="${escapeHtml(language)}" ${state.reviewLanguageFilter === language ? 'selected' : ''}>${escapeHtml(language)}</option>`).join('')}</select><select id="history-status-filter" class="select" aria-label="Filter by status"><option value="all">All Status</option><option value="completed" ${state.reviewStatusFilter === 'completed' ? 'selected' : ''}>Completed</option></select></div><button type="button" class="button button-primary" data-route="new-review">New Review</button></div>
      <div class="table-wrap">${reviews.length ? `<table class="data-table"><thead><tr><th>Project</th><th>Language</th><th>Score</th><th>Issues</th><th>Date</th><th>Status</th><th></th></tr></thead><tbody>${pageReviews.map((review) => `<tr><td><button type="button" class="table-link" data-action="open-saved-review" data-review-id="${escapeHtml(review.review_id)}">${escapeHtml(review.project_name)}</button></td><td>${escapeHtml(review.language)}</td><td><span class="score-plain">Not scored</span></td><td>${escapeHtml(String(review.finding_count))}</td><td>${escapeHtml(formatReviewDate(review.created_at))}</td><td><span class="status-pill">${escapeHtml(review.status)}</span></td><td><button type="button" class="icon-button row-open" data-action="open-saved-review" data-review-id="${escapeHtml(review.review_id)}" aria-label="Open review">${icons.chevron}</button></td></tr>`).join('')}</tbody></table>` : `<div class="panel-empty">${escapeHtml(state.reviewsError || (state.reviewsLoading ? 'Loading saved reviews...' : 'No saved reviews match this search.'))}${state.reviewsError ? '<button type="button" class="button button-secondary" data-action="retry-reviews">Retry</button>' : ''}</div>`}</div>
      <div class="table-footer"><span>Showing ${reviews.length ? state.historyPage * pageSize + 1 : 0}-${Math.min((state.historyPage + 1) * pageSize, reviews.length)} of ${reviews.length}</span><div class="pagination"><button type="button" class="button button-secondary" data-action="history-prev" ${state.historyPage === 0 ? 'disabled' : ''}>Previous</button><span>${state.historyPage + 1} / ${pageCount}</span><button type="button" class="button button-secondary" data-action="history-next" ${state.historyPage >= pageCount - 1 ? 'disabled' : ''}>Next</button></div></div>
    </div>
  `;
}

function getActiveFindings() {
  if (!state.reviewResult || state.reviewResult.error) return [];
  const normalized = normalizeReviewData(state.reviewResult);
  return [...normalized.bugs, ...normalized.security, ...normalized.performance, ...normalized.code_quality];
}

function renderFindingsPage() {
  const findings = getActiveFindings();
  if (!findings.length) {
    if (state.reviewResult && !state.reviewResult.error) return `<section class="panel empty-state"><div><h3>No findings in this review</h3><p>The selected review returned no findings for the available analyzers.</p></div></section>`;
    return renderUnavailablePage('Select a review to inspect its findings.');
  }
  const counts = findings.reduce((result, finding) => {
    const category = String(finding.agent || '').replace(' Agent', '');
    result[category] = (result[category] || 0) + 1;
    return result;
  }, {});
  const filtered = state.findingFilter === 'All' ? findings : findings.filter((finding) => String(finding.agent || '').replace(' Agent', '') === state.findingFilter);
  return `<div class="findings-page"><div class="panel-heading"><div><h3>${findings.length} findings</h3><p>From the selected review</p></div><span class="score-unavailable">${escapeHtml(state.reviewResult?.summary?.overall_risk_level || 'No score')}</span></div><div class="finding-filter-tabs"><button class="filter-chip ${state.findingFilter === 'All' ? 'active' : ''}" data-findings-filter="All">All ${findings.length}</button>${Object.entries(counts).map(([name, count]) => `<button class="filter-chip ${state.findingFilter === name ? 'active' : ''}" data-findings-filter="${escapeHtml(name)}">${escapeHtml(name)} ${count}</button>`).join('')}</div><div class="finding-list">${filtered.map((finding) => `<article class="finding-row"><span class="severity-flag ${riskClass(finding.severity)}">${escapeHtml(finding.severity)}</span><button type="button" class="finding-row-main" data-action="show-finding" data-finding-id="${escapeHtml(finding.id || '')}"><strong>${escapeHtml(finding.title)}</strong><span>${escapeHtml(finding.file || 'Unknown file')} · Line ${escapeHtml(String(finding.line_start || '—'))} · ${escapeHtml(finding.agent)}</span></button><span class="finding-arrow">${icons.chevron}</span></article>`).join('')}</div></div>`;
}

function renderAgentsPage() {
  const agents = state.reviewResult?.agents;
  const definitions = [
    ['Bug Agent', 'Correctness and runtime pattern checks', 'bug-heuristics'],
    ['Security Agent', 'Security pattern and trust-boundary checks', 'security-heuristics'],
    ['Performance Agent', 'Loop, blocking, and repeated-operation heuristics', 'performance-heuristics'],
    ['Code Quality Agent', 'Maintainability and dependency-graph heuristics', 'code-quality-heuristics'],
    ['Dependency Agent', 'Declared manifest and lockfile extraction', 'dependency-analysis'],
    ['Test Agent', 'Provider-backed tests for selected findings', 'provider-required'],
  ];
  return `<div class="agent-control"><div class="panel agent-orchestrator"><div class="agent-orchestrator-icon">${icons.settings}</div><div><span class="eyebrow">ORCHESTRATION</span><h3>Orchestrator Agent</h3><p>${state.reviewResult ? 'Latest review completed. No live event stream is available.' : 'Ready when a review is submitted.'}</p></div><span class="status-tag ${state.reviewResult ? 'complete' : ''}">${state.reviewResult ? 'Completed' : 'Idle'}</span></div><div class="agent-card-grid">${definitions.map(([name, description, key]) => { const result = Array.isArray(agents) ? agents.find((item) => item.agent === name) : null; const available = key !== 'provider-required'; return `<article class="agent-capability"><div class="agent-capability-head"><span class="metric-icon ${available ? 'teal' : 'gray'}">${icons.settings}</span><span class="status-tag ${result?.status === 'ok' ? 'complete' : result?.status === 'warning' ? 'warning' : ''}">${escapeHtml(result?.status || (available ? 'Ready' : 'Provider required'))}</span></div><h3>${escapeHtml(name)}</h3><p>${escapeHtml(description)}</p><small>${escapeHtml(result?.message || (available ? 'Deterministic analysis; no live status is exposed.' : 'Unavailable until an AI provider is configured.'))}</small></article>`; }).join('')}</div></div>`;
}

function renderCategoryPage(title, key) {
  const normalized = state.reviewResult ? normalizeReviewData(state.reviewResult) : null;
  const findings = normalized?.[key] || [];
  const securityCategories = key === 'security' ? `<div class="security-category-grid">${['Secrets','Authentication','Authorization','Injection','XSS','CSRF','Dependencies','Data Exposure','Configuration'].map((category) => `<div class="security-category"><span>${escapeHtml(category)}</span><small>Not separately classified</small></div>`).join('')}</div><p class="config-note">The current heuristic security findings do not emit these category classifications.</p>` : '';
  return `<div class="category-page">${key === 'security' ? `<section class="panel security-score-panel"><div><span class="eyebrow">SECURITY CENTER</span><h3>${findings.length} security finding${findings.length === 1 ? '' : 's'}</h3><p>No security score is produced by current analysis.</p></div><strong>Not scored</strong></section>` : ''}<section class="panel"><div class="panel-heading"><div><h3>${escapeHtml(title)} findings</h3><p>Selected review only</p></div><span class="severity-flag ${findings.length ? 'medium' : 'info'}">${findings.length}</span></div>${securityCategories}${findings.length ? renderFindingSection(title, findings) : '<div class="panel-empty">No findings are available for this category. Start or open a review first.</div>'}</section></div>`;
}

function renderTestGeneratorPage() {
  const tests = Object.values(state.findingWorkflows).map((workflow) => workflow.test).filter(Boolean);
  if (!tests.length) return renderUnavailablePage('No generated tests are available. Select a finding, generate a provider-backed fix, then request a focused test. Test execution is unavailable.');
  return `<section class="panel"><div class="panel-heading"><div><h3>Generated Tests</h3><p>Tests are suggestions only and have not been executed.</p></div><span class="status-tag warning">Execution unavailable</span></div><div class="test-list">${tests.map((test) => `<article class="test-row"><div><strong>${escapeHtml(test.purpose || 'Generated regression test')}</strong><p>${escapeHtml(test.framework || 'Framework unavailable')} · ${escapeHtml(test.status)}</p><small>Expected: ${escapeHtml(test.expected_behavior || 'Not specified')}</small>${test.test_code ? `<pre class="code-block">${escapeHtml(test.test_code)}</pre>` : ''}</div><span class="status-tag ${test.execution_status === 'EXECUTION_UNAVAILABLE' ? 'warning' : ''}">${escapeHtml(test.execution_status)}</span></article>`).join('')}</div></section>`;
}

function renderFixesPage() {
  const workflows = Object.values(state.findingWorkflows).filter((workflow) => workflow.fix);
  if (!workflows.length) return renderUnavailablePage('No fix proposals in this session. Open a finding and select Generate Fix. Original source is never changed automatically.');
  return `<div class="workflow-list">${workflows.map((workflow) => `<section class="panel workflow-panel"><div class="panel-heading"><div><h3>${escapeHtml(workflow.fix.file)}</h3><p>${escapeHtml(workflow.fix.finding?.title || 'Finding')}</p></div><span class="status-tag ${workflow.fix.status === 'GENERATED' ? 'complete' : 'warning'}">${escapeHtml(workflow.fix.status)}</span></div>${renderFindingWorkflow(workflow.fix.finding || { id: workflow.fix.finding_id })}</section>`).join('')}</div>`;
}

function renderReportsPage() {
  const result = state.reviewResult;
  if (!result || result.error) return renderUnavailablePage('Select a saved review to view its report.');
  const summary = result.summary || {};
  return `<section class="panel report-panel"><div class="report-brand"><span class="brand-mark">C</span><div><strong>CodeReview Agent</strong><small>AI Developer Team · Review Report</small></div><button class="button button-primary" type="button" data-action="download-report">Download Report</button></div><div class="report-metadata"><div><small>Project</small><strong>${escapeHtml(result.project?.project_name || result.filename || 'Code Review')}</strong></div><div><small>Language</small><strong>${escapeHtml(result.language?.language || (result.languages || []).map((item) => item.language).join(', ') || 'Unknown')}</strong></div><div><small>Files Analyzed</small><strong>${escapeHtml(String(result.file_count || summary.files_reviewed?.length || 1))}</strong></div><div><small>Review Date</small><strong>${escapeHtml(formatReviewDate(result.created_at) || 'Today')}</strong></div></div><div class="report-health"><span>Overall score</span><strong>Not scored</strong><small>No validated score is produced by current analyzers.</small></div><h3>Executive Summary</h3><p>${escapeHtml(summary.overall_risk_level ? `Highest detected severity: ${summary.overall_risk_level}.` : 'Analysis completed using the available review checks.')}</p><h3>Key Findings</h3>${renderFindingsPage()}</section>`;
}

function renderWorkspacePage() {
  return renderReviewPage();
}

function renderUnavailablePage(message) {
  return `<section class="panel empty-state"><div><h3>Nothing to show yet</h3><p>${escapeHtml(message)}</p><button type="button" class="button button-primary" data-route="new-review">Start a Review</button></div></section>`;
}

function renderSettingsPage() {
  const sections = ['General', 'Appearance', 'Review Preferences', 'AI Agents', 'GitHub', 'Notifications', 'Security'];
  const body = state.settingsSection === 'Appearance' ? `
    <div class="settings-section"><h3>Appearance</h3><p>Choose the visual theme for this browser.</p><label class="field"><span>Theme</span><select id="theme-select" class="select"><option value="light" ${state.theme === 'light' ? 'selected' : ''}>Light</option><option value="dark" ${state.theme === 'dark' ? 'selected' : ''}>Dark</option><option value="system" ${state.theme === 'system' ? 'selected' : ''}>System</option></select></label></div>
  ` : state.settingsSection === 'Review Preferences' ? `
    <div class="settings-section"><h3>Review Preferences</h3><p>Defaults are stored in this browser; review APIs still use their configured server behavior.</p><div class="settings-fields"><label class="field"><span>Default language</span><select id="preference-language" class="select">${languageOptions.map((language) => `<option ${((state.preferences.language || 'Auto Detect') === language) ? 'selected' : ''}>${escapeHtml(language)}</option>`).join('')}</select></label><label class="field"><span>Default review depth</span><select id="preference-depth" class="select">${['Quick','Standard','Deep'].map((depth) => `<option ${((state.preferences.depth || 'Standard') === depth) ? 'selected' : ''}>${depth}</option>`).join('')}</select></label><label class="field"><span>Severity threshold</span><select id="preference-severity" class="select">${['Info','Low','Medium','High','Critical'].map((level) => `<option ${((state.preferences.severity || 'Info') === level) ? 'selected' : ''}>${level}</option>`).join('')}</select></label></div><button type="button" class="button button-primary" data-action="save-preferences">Save Changes</button></div>
  ` : state.settingsSection === 'AI Agents' ? `
    <div class="settings-section"><h3>AI Agents</h3><p>Enabled analysis is determined by the current backend implementation.</p><div class="settings-status-row"><strong>Bug, Security, Performance, Code Quality</strong><span class="status-tag complete">Heuristics available</span></div><div class="settings-status-row"><strong>LLM Fix and Test generation</strong><span class="status-tag warning">Provider required</span></div><div class="settings-status-row"><strong>Test execution</strong><span class="status-tag warning">Unavailable</span></div></div>
  ` : state.settingsSection === 'GitHub' ? `
    <div class="settings-section"><h3>GitHub</h3><p>Repository integration is not connected.</p><span class="status-tag warning">Unavailable</span></div>
  ` : state.settingsSection === 'Notifications' ? `
    <div class="settings-section"><h3>Notifications</h3><p>No notification service is configured.</p><span class="status-tag warning">Unavailable</span></div>
  ` : state.settingsSection === 'Security' ? `
    <div class="settings-section"><h3>Security</h3><div class="settings-status-row"><strong>Submitted code execution</strong><span class="status-tag complete">Disabled</span></div><div class="settings-status-row"><strong>Authentication</strong><span class="status-tag warning">Not implemented</span></div><div class="settings-status-row"><strong>AI provider credentials</strong><span class="status-tag complete">Backend only</span></div></div>
  ` : `
    <div class="settings-section"><h3>General</h3><p>CodeReview Agent workspace preferences.</p><div class="settings-status-row"><strong>Signed-in profile</strong><span>${escapeHtml(currentUser().name || 'Charitha')}</span></div><div class="settings-status-row"><strong>Email</strong><span>${escapeHtml(currentUser().email || 'Not provided')}</span></div><div class="settings-status-row"><strong>Backend API</strong><code>${escapeHtml(API_BASE)}</code></div></div>
  `;
  return `<div class="settings-layout"><nav class="settings-nav" aria-label="Settings sections">${sections.map((section) => `<button type="button" class="settings-nav-item ${state.settingsSection === section ? 'active' : ''}" data-settings-section="${escapeHtml(section)}">${escapeHtml(section)}</button>`).join('')}</nav><section class="panel settings-content">${body}</section></div>`;
}

function renderHelpPage() {
  return `
    <div class="card settings-card">
      <h3>Help & Documentation</h3>
      <p>Use the review workflow to analyze code, review findings, inspect fixes, and generate tests. The interface is connected to the existing backend API endpoints without altering the server contract.</p>
      <ul>
        <li><strong>Review endpoint:</strong> /api/review</li>
        <li><strong>Language detection:</strong> /api/detect-language</li>
        <li><strong>Batch review:</strong> /api/review/batch</li>
      </ul>
      <div class="action-row">
        <button type="button" class="button button-primary" data-route="new-review">Start a new review</button>
      </div>
    </div>
  `;
}

function renderActiveResultPanel() {
  const payload = normalizeReviewData(state.reviewResult || {});
  const overviewCount = payload.bugs.length + payload.security.length + payload.performance.length + payload.code_quality.length;

  if (!state.reviewResult) {
    return `
      <div class="empty-state">
        <div>
          <h3>No review started yet</h3>
          <p>Start your first AI-powered code review.</p>
          <div class="action-row" style="justify-content:center; margin-top:16px;">
            <button type="button" class="button button-primary" data-route="new-review">Start Review</button>
          </div>
        </div>
      </div>
    `;
  }

  if (state.reviewResult.error) {
    return `
      <div class="empty-state">
        <div>
          <h3>Unable to connect to review service</h3>
          <p>${escapeHtml(state.reviewResult.error)}</p>
          <div class="action-row" style="justify-content:center; margin-top:16px;">
            <button type="button" class="button button-primary" id="retry-review-btn">Retry</button>
          </div>
        </div>
      </div>
    `;
  }

  const activeTab = state.currentTab || 'overview';

  if (activeTab === 'overview') {
    const summary = payload.summary || {};
    if (payload.project) return renderProjectOverview(payload);
    return `
      <div>
        <div class="section-header">
          <h3>Review Overview</h3>
          <span class="badge ${riskClass(summary.overall_risk_level || 'LOW')}">${escapeHtml(summary.overall_risk_level || 'LOW')}</span>
        </div>
        <div class="overview-grid">
          <div class="metric-card">
            <span class="label">Language</span>
            <strong>${escapeHtml(payload.language?.language || 'Unknown')}</strong>
          </div>
          <div class="metric-card">
            <span class="label">Framework</span>
            <strong>${escapeHtml(payload.language?.framework || 'Not detected')}</strong>
          </div>
          <div class="metric-card">
            <span class="label">Files reviewed</span>
            <strong>${escapeHtml(String((summary.files_reviewed || []).length || 1))}</strong>
          </div>
          <div class="metric-card">
            <span class="label">Lines reviewed</span>
            <strong>${escapeHtml(String(summary.lines_reviewed || 0))}</strong>
          </div>
          <div class="metric-card">
            <span class="label">Detection confidence</span>
            <strong>${escapeHtml(String(Number(payload.language?.confidence || 0).toFixed(2)))}</strong>
          </div>
          <div class="metric-card">
            <span class="label">Risk level</span>
            <strong>${escapeHtml(summary.overall_risk_level || 'LOW')}</strong>
          </div>
        </div>

        <div class="overview-grid">
          <div class="metric-card"><span class="label">Bugs</span><strong>${payload.bugs.length}</strong></div>
          <div class="metric-card"><span class="label">Security</span><strong>${payload.security.length}</strong></div>
          <div class="metric-card"><span class="label">Performance</span><strong>${payload.performance.length}</strong></div>
          <div class="metric-card"><span class="label">Code Quality</span><strong>${payload.code_quality.length}</strong></div>
        </div>

        <div class="finding-card">
          <h4 style="margin:0 0 12px;">Summary</h4>
          <p>${escapeHtml(payload.summary?.language || 'Review completed successfully.')}</p>
          <p>${escapeHtml(overviewCount ? `${overviewCount} findings detected across analysis layers.` : 'No issues detected in this review.')}</p>
        </div>
      </div>
    `;
  }

  if (activeTab === 'bugs') return renderFindingSection('Bugs', payload.bugs);
  if (activeTab === 'security') return renderFindingSection('Security', payload.security);
  if (activeTab === 'performance') return renderFindingSection('Performance', payload.performance);
  if (activeTab === 'code_quality') return renderFindingSection('Code Quality', payload.code_quality);
  if (activeTab === 'tests') return renderTestsSection(payload.tests || []);
  if (activeTab === 'fixes') return renderFixesSection(payload.fixes || []);
  if (activeTab === 'report') return renderFinalReport(payload);

  return renderFindingSection('Overview', payload.bugs);
}

function renderProjectOverview(payload) {
  const treeLines = [];
  const visit = (node, depth = 0) => {
    treeLines.push(`${'  '.repeat(depth)}${node.name}${node.type === 'directory' ? '/' : ''}`);
    (node.children || []).forEach((child) => visit(child, depth + 1));
  };
  if (payload.file_tree) visit(payload.file_tree);

  return `
    <div>
      <div class="section-header">
        <h3>${escapeHtml(payload.project.project_name || 'Project Review')}</h3>
        <span class="badge ${riskClass(payload.summary?.overall_risk_level || 'LOW')}">${escapeHtml(payload.summary?.overall_risk_level || 'LOW')}</span>
      </div>
      <div class="overview-grid">
        <div class="metric-card"><span class="label">Files</span><strong>${escapeHtml(String(payload.file_count || 0))}</strong></div>
        <div class="metric-card"><span class="label">Languages</span><strong>${escapeHtml((payload.languages || []).map((item) => item.language).join(', ') || 'Unknown')}</strong></div>
        <div class="metric-card"><span class="label">Framework</span><strong>${escapeHtml(payload.project.framework || 'Not detected')}</strong></div>
        <div class="metric-card"><span class="label">Findings</span><strong>${escapeHtml(String((payload.findings || []).length))}</strong></div>
        <div class="metric-card"><span class="label">Relationships</span><strong>${escapeHtml(String((payload.relationships || []).length))}</strong></div>
      </div>
      <div class="review-shell">
        <article class="finding-card">
          <h4>Project Structure</h4>
          <div class="code-block">${escapeHtml(treeLines.join('\n'))}</div>
        </article>
        <article class="finding-card">
          <h4>Agent Status</h4>
          ${(payload.agents || []).map((agent) => `<p><strong>${escapeHtml(agent.agent)}</strong>: ${escapeHtml(agent.status)}${agent.message ? `, ${escapeHtml(agent.message)}` : ''}</p>`).join('')}
          <h4>Analysis Capabilities</h4>
          <p>AI: ${escapeHtml(payload.analysis_capabilities?.ai_analysis || 'UNAVAILABLE')}</p>
          <p>Syntax parsing: ${escapeHtml(payload.analysis_capabilities?.syntax_analysis || 'Unavailable')}</p>
        </article>
      </div>
      <div class="findings-stack">
        ${(payload.findings || []).slice(0, 8).map((finding) => `
          <article class="finding-card">
            <div class="finding-top"><h4>${escapeHtml(finding.title)}</h4><span class="badge ${riskClass(finding.severity)}">${escapeHtml(finding.severity)}</span></div>
            <div class="meta-line"><span>${escapeHtml(finding.agent)}</span><span>File: ${escapeHtml(finding.file)}</span><span>Line ${escapeHtml(String(finding.line_start || 1))}</span></div>
            <p>${escapeHtml(finding.description)}</p>
            <div class="code-block">${escapeHtml(finding.evidence || '')}</div>
          </article>
        `).join('')}
      </div>
    </div>
  `;
}

function renderFindingSection(title, items) {
  if (!Array.isArray(items) || !items.length) {
    return `
      <div class="empty-state">
        <div>
          <h3>No ${title.toLowerCase()} findings</h3>
          <p>The analysis completed without any ${title.toLowerCase()} issues.</p>
        </div>
      </div>
    `;
  }

  return `
    <div class="findings-stack">
      ${items.map((item) => `
        <article class="finding-card">
          <div class="finding-top">
            <h4>${escapeHtml(item.title || 'Finding')}</h4>
            <span class="badge ${riskClass(item.severity || 'INFO')}">${escapeHtml(item.severity || 'INFO')}</span>
          </div>
          <div class="meta-line">
            <span>${escapeHtml(item.agent || 'Analysis Agent')}</span>
            <span>•</span>
            <span>File: ${escapeHtml(item.file || 'input')}</span>
            <span>•</span>
            <span>Line ${escapeHtml(String(item.line_start || 1))}</span>
          </div>
          <p>${escapeHtml(item.description || 'No description available.')}</p>
          <div class="meta-line"><strong>Evidence</strong></div>
          <div class="code-block">${escapeHtml(item.evidence || 'No evidence snippet provided.')}</div>
          <div class="meta-line" style="margin-top:12px;"><strong>Recommendation</strong></div>
          <p>${escapeHtml(item.recommendation || 'Review the issue and apply a focused fix.')}</p>
          <div class="action-row">
            <button type="button" class="button button-secondary" data-action="copy-snippet" data-value="${escapeHtml(item.evidence || item.description || '')}">Copy</button>
            <button type="button" class="button button-ghost">View Context</button>
            ${item.id ? `<button type="button" class="button button-secondary" data-action="generate-fix" data-finding-id="${escapeHtml(item.id)}">Generate Fix</button>` : ''}
          </div>
          ${item.id ? renderFindingWorkflow(item) : ''}
        </article>
      `).join('')}
    </div>
  `;
}

function renderFindingWorkflow(finding) {
  const workflow = state.findingWorkflows[finding.id];
  if (!workflow) return '';
  const fix = workflow.fix;
  const test = workflow.test;
  const verification = workflow.verification;
  const fixPanel = fix ? `
    <section class="diff-box" aria-label="Proposed fix">
      <div class="finding-top">
        <h4>Proposed Fix</h4>
        <span class="badge info">${escapeHtml(fix.status === 'GENERATED' ? 'AI GENERATED' : fix.status)}</span>
      </div>
      <p>${escapeHtml(fix.explanation || '')}</p>
      <p>Confidence: ${escapeHtml(String(fix.confidence))}%</p>
      <p>Validation: ${escapeHtml(fix.validation_status)}</p>
      <div class="diff-row">
        <div class="diff-pane removed"><h4>BEFORE</h4><div class="code-block">${escapeHtml(fix.original_code || '')}</div></div>
        <div class="diff-pane added"><h4>PROPOSED</h4><div class="code-block">${escapeHtml(fix.fixed_code || 'No proposed source.')}</div></div>
      </div>
      ${fix.diff ? `<h4>Unified diff</h4><div class="code-block">${escapeHtml(fix.diff)}</div>` : ''}
      <div class="action-row">
        ${fix.status === 'GENERATED' ? `<button type="button" class="button button-secondary" data-action="generate-finding-test" data-fix-id="${escapeHtml(fix.fix_id)}">Generate Test</button><button type="button" class="button button-secondary" data-action="verify-finding-fix" data-fix-id="${escapeHtml(fix.fix_id)}">Verify Fix</button>` : ''}
      </div>
    </section>
  ` : '';
  const testPanel = test ? `
    <section class="finding-card">
      <h4>Generated Test</h4>
      <p>Status: ${escapeHtml(test.status)} | Framework: ${escapeHtml(test.framework || 'Unavailable')}</p>
      <p>Validation: ${escapeHtml(test.validation_status)} | Execution: ${escapeHtml(test.execution_status)}</p>
      <p>${escapeHtml(test.purpose || '')}</p>
      ${test.test_code ? `<div class="code-block">${escapeHtml(test.test_code)}</div>` : ''}
      <p>Expected behavior: ${escapeHtml(test.expected_behavior || '')}</p>
    </section>
  ` : '';
  const verificationPanel = verification ? `
    <section class="finding-card">
      <h4>Verification: ${escapeHtml(verification.status)}</h4>
      <p>${escapeHtml(verification.explanation)}</p>
      <ul>${(verification.checks || []).map((check) => `<li>${escapeHtml(check.name)}: ${escapeHtml(check.status)}. ${escapeHtml(check.details)}</li>`).join('')}</ul>
    </section>
  ` : '';
  return `<div class="findings-stack" style="margin-top:14px;">${fixPanel}${testPanel}${verificationPanel}</div>`;
}

function findingById(findingId) {
  const result = state.reviewResult || {};
  const collections = [result.bugs, result.security, result.performance, result.code_quality, result.findings];
  for (const collection of collections) {
    if (!Array.isArray(collection)) continue;
    const match = collection.find((finding) => finding.id === findingId);
    if (match) return match;
  }
  return null;
}

function fixRequestForFinding(finding) {
  const result = state.reviewResult || {};
  const projectFile = Array.isArray(result.files) ? result.files.find((file) => file.path === finding.file) : null;
  const uploadedProjectFile = state.projectFiles.find((file) => file.path === finding.file);
  const sourceCode = uploadedProjectFile?.content || result.source_code || null;
  if (typeof sourceCode !== 'string') throw new Error('Original source for this finding is not available in the current review.');

  let language = result.language?.language || 'Unknown';
  if (projectFile?.language && projectFile.language !== 'Unknown') language = projectFile.language;
  if (language === 'Unknown') throw new Error('The finding language could not be determined.');

  const relatedPaths = new Set((result.relationships || [])
    .filter((edge) => edge.source === finding.file || edge.target === finding.file)
    .map((edge) => edge.source === finding.file ? edge.target : edge.source));
  const relatedFiles = [...relatedPaths]
    .map((path) => state.projectFiles.find((file) => file.path === path))
    .filter(Boolean)
    .slice(0, 20)
    .map((file) => ({ path: file.path, content: file.content.slice(0, PROJECT_LIMITS.relatedFileChars) }));
  let relatedChars = 0;
  const boundedRelatedFiles = relatedFiles.map((file) => {
    const remaining = Math.max(0, PROJECT_LIMITS.contextChars - relatedChars);
    const content = file.content.slice(0, remaining);
    relatedChars += content.length;
    return { ...file, content };
  }).filter((file) => file.content.length > 0);

  return {
    finding,
    source_code: sourceCode,
    filename: finding.file || result.filename || 'input',
    language,
    framework: result.project?.framework || result.language?.framework || null,
    project_context: {
      project: result.project || null,
      metadata: result.metadata || {},
      dependencies: result.dependencies || [],
      relationships: (result.relationships || []).filter((edge) => edge.source === finding.file || edge.target === finding.file),
    },
    related_files: boundedRelatedFiles,
  };
}

function attachFindingWorkflowListeners() {
  document.querySelectorAll('[data-action="generate-fix"]').forEach((button) => {
    button.addEventListener('click', async () => {
      const finding = findingById(button.dataset.findingId);
      if (!finding) return toast('Finding is no longer available.', 'error');
      try {
        const payload = fixRequestForFinding(finding);
        const result = await requestJson(`/findings/${encodeURIComponent(finding.id)}/fix`, {
          method: 'POST',
          body: JSON.stringify(payload),
        });
        state.findingWorkflows[finding.id] = { fix: result, test: null, verification: null };
        renderApp();
        toast(result.status === 'GENERATED' ? 'Proposed fix generated for review.' : result.explanation, result.status === 'GENERATED' ? 'success' : 'warning');
      } catch (error) {
        toast(error.message, 'error');
      }
    });
  });

  document.querySelectorAll('[data-action="generate-finding-test"]').forEach((button) => {
    button.addEventListener('click', async () => {
      try {
        const result = await requestJson(`/fixes/${encodeURIComponent(button.dataset.fixId)}/generate-test`, {
          method: 'POST',
          body: JSON.stringify({}),
        });
        const workflow = Object.values(state.findingWorkflows).find((item) => item.fix?.fix_id === button.dataset.fixId);
        if (workflow) workflow.test = result;
        renderApp();
        toast(result.status === 'GENERATED' ? 'Test generated; execution is unavailable.' : result.purpose, result.status === 'GENERATED' ? 'success' : 'warning');
      } catch (error) {
        toast(error.message, 'error');
      }
    });
  });

  document.querySelectorAll('[data-action="verify-finding-fix"]').forEach((button) => {
    button.addEventListener('click', async () => {
      try {
        const workflow = Object.values(state.findingWorkflows).find((item) => item.fix?.fix_id === button.dataset.fixId);
        const result = await requestJson(`/fixes/${encodeURIComponent(button.dataset.fixId)}/verify`, {
          method: 'POST',
          body: JSON.stringify(workflow?.test?.test_id ? { test_id: workflow.test.test_id } : {}),
        });
        if (workflow) workflow.verification = result;
        renderApp();
      } catch (error) {
        toast(error.message, 'error');
      }
    });
  });
}

function renderTestsSection(tests) {
  if (!Array.isArray(tests) || !tests.length) {
    return `
      <div class="empty-state">
        <div>
          <h3>No generated tests</h3>
          <p>There are no generated tests for this code yet.</p>
        </div>
      </div>
    `;
  }

  return `
    <div class="findings-stack">
      ${tests.map((test, index) => `
        <article class="finding-card">
          <div class="finding-top">
            <h4>${escapeHtml(test.name || `Generated Test ${index + 1}`)}</h4>
            <span class="badge info">${escapeHtml(test.kind || 'unit')}</span>
          </div>
          <div class="meta-line">
            <span>Framework: ${escapeHtml(test.framework || 'Unknown')}</span>
            <span>•</span>
            <span>Coverage: ${escapeHtml(test.coverage || 'General')}</span>
          </div>
          <div class="code-block">${escapeHtml(test.test_code || 'No generated source available.')}</div>
          <div class="action-row">
            <button type="button" class="button button-secondary" data-action="copy-snippet" data-value="${escapeHtml(test.test_code || '')}">Copy Test</button>
          </div>
        </article>
      `).join('')}
    </div>
  `;
}

function renderFixesSection(fixes) {
  const generatedFixes = Array.isArray(fixes) ? fixes.filter((fix) => fix.status === 'GENERATED' && fix.fixed_code) : [];
  if (!generatedFixes.length) {
    return `
      <div class="empty-state">
        <div>
          <h3>No generated fixes</h3>
          <p>Fix generation requires a specific finding and an available AI provider. Generate a proposal from an individual finding.</p>
        </div>
      </div>
    `;
  }

  return `
    <div class="findings-stack">
      ${generatedFixes.map((fix, index) => `
        <article class="finding-card">
          <div class="finding-top">
            <h4>Suggested Fix ${index + 1}</h4>
            <span class="badge info">AI GENERATED</span>
          </div>
          <p>${escapeHtml(fix.explanation || 'Apply the recommended change to address the issue.')}</p>
          <div class="diff-box">
            <div class="diff-row">
              <div class="diff-pane removed">
                <h4>Original Code</h4>
                <div class="code-block">${escapeHtml(fix.original_code || 'No original snippet provided.')}</div>
              </div>
              <div class="diff-pane added">
                <h4>Suggested Fix</h4>
                <div class="code-block">${escapeHtml(fix.corrected_code || 'No corrected snippet available.')}</div>
              </div>
            </div>
          </div>
          <div class="action-row">
            <button type="button" class="button button-secondary" data-action="copy-snippet" data-value="${escapeHtml(fix.corrected_code || '')}">Copy Fix</button>
          </div>
        </article>
      `).join('')}
    </div>
  `;
}

function renderFinalReport(payload) {
  const summary = payload.summary || {};
  return `
    <div class="finding-card">
      <div class="section-header">
        <h3>Code Review Report</h3>
        <div class="action-row">
          <button type="button" class="button button-ghost" data-action="copy-report">Copy Report</button>
          <button type="button" class="button button-secondary" disabled>Export PDF (coming soon)</button>
        </div>
      </div>
      <p><strong>Project:</strong> ${escapeHtml(payload.filename || 'example.py')}</p>
      <p><strong>Risk:</strong> <span class="badge ${riskClass(summary.overall_risk_level || 'LOW')}">${escapeHtml(summary.overall_risk_level || 'LOW')}</span></p>
      <h4>Executive Summary</h4>
      <p>${escapeHtml(payload.summary?.language || 'The analysis completed successfully and flagged a range of findings. Review the tabs above for details.')}</p>
      <h4>Critical Findings</h4>
      <p>${escapeHtml((payload.bugs || []).length ? 'The code review produced actionable bug and vulnerability findings that should be prioritized by severity.' : 'No critical issues were identified at the current review depth.')}</p>
      <h4>Recommended Actions</h4>
      <ul>
        <li>Prioritize remediation for all HIGH and CRITICAL findings.</li>
        <li>Increase unit test coverage for the vulnerable code paths.</li>
        <li>Validate any suggested fix in a staging environment before deployment.</li>
      </ul>
      <div class="code-block">${escapeHtml(JSON.stringify(payload, null, 2))}</div>
    </div>
  `;
}

function bindAuthEventHandlers() {
  document.getElementById('signin-form')?.addEventListener('submit', (event) => {
    event.preventDefault();
    const email = document.getElementById('signin-email').value.trim();
    const password = document.getElementById('signin-password').value;

    if (!email || !password) {
      toast('Please enter both email and password.', 'error');
      return;
    }

    state.session = {
      name: 'Demo User',
      email,
    };
    saveSession();
    state.route = 'dashboard';
    renderApp();
    toast('Signed in successfully', 'success');
  });

  document.getElementById('signup-form')?.addEventListener('submit', (event) => {
    event.preventDefault();
    const name = document.getElementById('signup-name').value.trim();
    const email = document.getElementById('signup-email').value.trim();
    const password = document.getElementById('signup-password').value;
    const confirm = document.getElementById('signup-confirm').value;

    if (!name || !email || !password || !confirm) {
      toast('Please complete all fields.', 'error');
      return;
    }

    if (password !== confirm) {
      toast('Passwords do not match.', 'error');
      return;
    }

    state.session = { name, email };
    saveSession();
    state.route = 'dashboard';
    renderApp();
    toast('Account created in demo mode', 'success');
  });

  document.getElementById('forgot-form')?.addEventListener('submit', (event) => {
    event.preventDefault();
    const email = document.getElementById('forgot-email').value.trim();
    if (!email) {
      toast('Enter your email to receive a reset link.', 'error');
      return;
    }
    toast('Password reset link queued in demo mode.', 'success');
  });

  document.querySelectorAll('[data-route]').forEach((button) => {
    button.addEventListener('click', () => {
      const route = button.dataset.route;
      if (route === 'signin' || route === 'signup' || route === 'forgot') {
        state.route = route;
        renderApp();
        return;
      }
      state.route = route;
      renderApp();
    });
  });
}

function bindShellEvents() {
  const navButtons = document.querySelectorAll('[data-route]');
  navButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const route = button.dataset.route;
      if (route === 'signin' || route === 'signup' || route === 'forgot') {
        state.route = route;
        renderApp();
        return;
      }
      state.route = route;
      if (route === 'workspace') state.reviewMode = 'project';
      state.sidebarOpen = false;
      renderApp();
    });
  });

  document.querySelector('[data-action="open-sidebar"]')?.addEventListener('click', () => {
    state.sidebarOpen = true;
    renderApp();
  });
  document.querySelector('[data-action="close-sidebar"]')?.addEventListener('click', () => {
    state.sidebarOpen = false;
    renderApp();
  });

  document.getElementById('global-review-search')?.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    state.reviewSearch = event.target.value;
    state.route = 'history';
    state.sidebarOpen = false;
    renderApp();
  });
  document.getElementById('history-search')?.addEventListener('input', (event) => {
    state.reviewSearch = event.target.value;
    state.historyPage = 0;
    const cursor = event.target.selectionStart;
    renderApp();
    const search = document.getElementById('history-search');
    search?.focus();
    search?.setSelectionRange(cursor, cursor);
  });
  document.getElementById('history-language-filter')?.addEventListener('change', (event) => {
    state.reviewLanguageFilter = event.target.value;
    state.historyPage = 0;
    renderApp();
  });
  document.getElementById('history-status-filter')?.addEventListener('change', (event) => {
    state.reviewStatusFilter = event.target.value;
    state.historyPage = 0;
    renderApp();
  });
  document.querySelector('[data-action="history-prev"]')?.addEventListener('click', () => {
    state.historyPage = Math.max(0, state.historyPage - 1);
    renderApp();
  });
  document.querySelector('[data-action="history-next"]')?.addEventListener('click', () => {
    state.historyPage += 1;
    renderApp();
  });
  document.querySelectorAll('[data-findings-filter]').forEach((button) => {
    button.addEventListener('click', () => {
      state.findingFilter = button.dataset.findingsFilter;
      renderApp();
    });
  });
  document.querySelector('[data-action="retry-reviews"]')?.addEventListener('click', () => {
    state.reviewsLoaded = false;
    state.reviewsError = '';
    renderApp();
  });

  document.querySelector('[data-action="logout"]')?.addEventListener('click', () => {
    localStorage.removeItem('codeReviewSession');
    state.session = null;
    state.route = 'signin';
    renderApp();
    toast('Logged out', 'success');
  });

  document.getElementById('theme-toggle')?.addEventListener('click', () => {
    const nextTheme = state.theme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    renderApp();
  });

  document.getElementById('theme-select')?.addEventListener('change', (event) => {
    const value = event.target.value;
    setTheme(value);
    renderApp();
  });

  document.querySelectorAll('[data-settings-section]').forEach((button) => {
    button.addEventListener('click', () => {
      state.settingsSection = button.dataset.settingsSection;
      renderApp();
    });
  });
  document.querySelector('[data-action="save-preferences"]')?.addEventListener('click', () => {
    state.preferences = {
      language: document.getElementById('preference-language')?.value || 'Auto Detect',
      depth: document.getElementById('preference-depth')?.value || 'Standard',
      severity: document.getElementById('preference-severity')?.value || 'Info',
    };
    localStorage.setItem('codeReviewPreferences', JSON.stringify(state.preferences));
    toast('Review preferences saved in this browser.', 'success');
  });

  document.querySelectorAll('[data-action="open-review"]').forEach((button) => {
    button.addEventListener('click', () => {
      state.route = 'new-review';
      renderApp();
    });
  });

  document.querySelectorAll('[data-action="copy-snippet"]').forEach((button) => {
    button.addEventListener('click', async () => {
      const text = button.dataset.value || '';
      try {
        await navigator.clipboard.writeText(text);
        toast('Copied to clipboard', 'success');
      } catch {
        toast('Clipboard access unavailable', 'warning');
      }
    });
  });

  document.querySelectorAll('[data-action="copy-report"]').forEach((button) => {
    button.addEventListener('click', async () => {
      const text = JSON.stringify(state.reviewResult || {}, null, 2);
      try {
        await navigator.clipboard.writeText(text);
        toast('Report copied to clipboard', 'success');
      } catch {
        toast('Unable to copy report', 'warning');
      }
    });
  });

  document.querySelectorAll('[data-action="open-saved-review"]').forEach((button) => {
    button.addEventListener('click', async () => {
      try {
        const result = await requestJson(`/review/${encodeURIComponent(button.dataset.reviewId)}`);
        state.reviewResult = result;
        state.selectedReviewId = result.review_id;
        state.reviewMode = result.project ? 'project' : 'single';
        state.projectFiles = [];
        state.findingWorkflows = {};
        state.currentTab = 'overview';
        state.route = 'reports';
        renderApp();
      } catch (error) {
        toast(error.message, 'error');
      }
    });
  });

  document.querySelector('[data-action="download-report"]')?.addEventListener('click', () => {
    const content = JSON.stringify(state.reviewResult || {}, null, 2);
    const blob = new Blob([content], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `review-${state.reviewResult?.review_id || 'report'}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  });

  document.querySelectorAll('[data-action="show-finding"]').forEach((button) => {
    button.addEventListener('click', () => {
      state.route = 'new-review';
      state.currentTab = 'overview';
      renderApp();
      document.querySelector(`[data-finding-id="${CSS.escape(button.dataset.findingId)}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  });

}

function attachReviewPageListeners() {
  document.querySelectorAll('input[name="review-mode"]').forEach((input) => {
    input.addEventListener('change', () => {
      state.reviewMode = input.value;
      renderApp();
    });
  });

  document.getElementById('review-code-btn')?.addEventListener('click', async () => {
    if (state.reviewMode === 'project') {
      if (!state.projectFiles.length) {
        toast('Add at least one project file before starting a review.', 'error');
        return;
      }
      const payload = {
        project_name: document.getElementById('project-name-input').value.trim() || 'Code Review Project',
        entry_file: document.getElementById('project-entry-input').value || null,
        files: state.projectFiles.map((file) => ({ path: file.path, content: file.content })),
      };
      const reviewContainer = document.getElementById('review-results-body');
      reviewContainer.innerHTML = '<div class="loading-shell"><div class="loading-row"><div class="spinner"></div> Analyzing project files...</div></div>';
      try {
        const response = await requestJson('/reviews/project', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
        state.projectName = payload.project_name;
        state.projectEntryFile = payload.entry_file || '';
        state.findingWorkflows = {};
        state.reviewResult = response;
        state.currentTab = 'overview';
        renderApp();
        refreshPersistedReviews();
        toast('Project review completed', 'success');
      } catch (error) {
        state.reviewResult = { error: error.message };
        renderApp();
        toast(error.message, 'error');
      }
      return;
    }

    const code = document.getElementById('code-editor').value;
    const filename = document.getElementById('filename-input').value || 'example.py';
    const language = document.getElementById('language-select').value === 'Auto Detect' ? 'auto' : document.getElementById('language-select').value;

    if (!code.trim()) {
      toast('Enter code before starting a review.', 'error');
      return;
    }
    if (code.length > MAX_CODE_CHARS) {
      toast(`Code exceeds the ${MAX_CODE_CHARS.toLocaleString()} character limit.`, 'error');
      return;
    }

    const reviewContainer = document.getElementById('review-results-body');
    reviewContainer.innerHTML = `
      <div class="loading-shell">
        <div class="loading-row"><div class="spinner"></div> Analyzing your code...</div>
        <ul class="status-list">
          <li><span>Language Detection</span><span class="checkmark">✓</span></li>
          <li><span>Bug Agent</span><span class="checkmark">✓</span></li>
          <li><span>Security Agent</span><span class="spinner" style="width:12px;height:12px;"></span></li>
          <li><span>Performance Agent</span><span class="spinner" style="width:12px;height:12px;"></span></li>
          <li><span>Test Agent</span><span class="spinner" style="width:12px;height:12px;"></span></li>
          <li><span>Fix Agent</span><span class="spinner" style="width:12px;height:12px;"></span></li>
        </ul>
      </div>
    `;

    try {
      const response = await requestJson('/review', {
        method: 'POST',
        body: JSON.stringify({ language, filename, code }),
      });

      state.findingWorkflows = {};
      state.reviewResult = { ...response, filename, source_code: code };
      state.currentTab = 'overview';
      renderApp();
      refreshPersistedReviews();
      toast('Review completed', 'success');
    } catch (error) {
      state.reviewResult = { error: error.message, filename };
      renderApp();
      toast(error.message, 'error');
    }
  });

  document.getElementById('detect-language-btn')?.addEventListener('click', async () => {
    const code = document.getElementById('code-editor').value;
    const filename = document.getElementById('filename-input').value || 'example.py';
    const language = document.getElementById('language-select').value === 'Auto Detect' ? 'auto' : document.getElementById('language-select').value;

    if (!code.trim()) {
      toast('Enter code before detecting a language.', 'error');
      return;
    }
    if (code.length > MAX_CODE_CHARS) {
      toast(`Code exceeds the ${MAX_CODE_CHARS.toLocaleString()} character limit.`, 'error');
      return;
    }

    try {
      const response = await requestJson('/detect-language', {
        method: 'POST',
        body: JSON.stringify({ code, filename, language }),
      });
      state.reviewResult = { ...response, filename, language: response };
      state.currentTab = 'overview';
      renderApp();
      toast('Language detected', 'success');
    } catch (error) {
      toast(error.message, 'error');
    }
  });

  document.getElementById('clear-editor-btn')?.addEventListener('click', () => {
    document.getElementById('code-editor').value = '';
    toast('Editor cleared', 'success');
  });

  document.getElementById('file-upload-input')?.addEventListener('change', async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (file.size > MAX_CODE_CHARS) {
      toast(`File exceeds the ${MAX_CODE_CHARS.toLocaleString()} character upload limit.`, 'error');
      event.target.value = '';
      return;
    }

    try {
      const text = await file.text();
      if (text.length > MAX_CODE_CHARS) {
        toast(`File exceeds the ${MAX_CODE_CHARS.toLocaleString()} character upload limit.`, 'error');
        event.target.value = '';
        return;
      }
      document.getElementById('code-editor').value = text;
      document.getElementById('filename-input').value = file.name || 'uploaded-file';
      const extension = file.name.split('.').pop()?.toLowerCase();
      const normalized = {
        py: 'Python', js: 'JavaScript', ts: 'TypeScript', jsx: 'JavaScript', tsx: 'TypeScript', java: 'Java', go: 'Go', rs: 'Rust', cs: 'C#', sql: 'SQL', sh: 'Shell', html: 'HTML', css: 'CSS'
      };
      const nextLanguage = normalized[extension] || 'Auto Detect';
      document.getElementById('language-select').value = nextLanguage;
      toast(`${file.name} loaded`, 'success');
    } catch {
      toast('The selected file could not be read.', 'error');
    }
  });

  document.getElementById('project-name-input')?.addEventListener('input', (event) => {
    state.projectName = event.target.value;
  });

  document.getElementById('project-entry-input')?.addEventListener('change', (event) => {
    state.projectEntryFile = event.target.value;
  });

  document.querySelectorAll('[data-workspace-file]').forEach((button) => {
    button.addEventListener('click', () => {
      state.currentWorkspacePath = button.dataset.workspaceFile;
      renderApp();
    });
  });

  document.getElementById('project-upload-input')?.addEventListener('change', async (event) => {
    const selected = Array.from(event.target.files || []);
    if (!selected.length) return;

    try {
      const loaded = [];
      let totalBytes = state.projectFiles.reduce((total, file) => total + file.size, 0);
      const existingPaths = new Set(state.projectFiles.map((file) => file.path.toLowerCase()));
      for (const file of selected) {
        const path = (file.webkitRelativePath || file.name).replace(/\\/g, '/');
        const filename = path.split('/').pop();
        if (!path || path.startsWith('/') || path.split('/').some((part) => part === '..' || part === '.' || part === '')) {
          throw new Error('A selected file has an unsafe relative path.');
        }
        if (path.length > PROJECT_LIMITS.pathChars || filename.length > PROJECT_LIMITS.filenameChars) {
          throw new Error(`A selected project path exceeds the ${PROJECT_LIMITS.pathChars} character limit.`);
        }
        if (existingPaths.has(path.toLowerCase())) {
          throw new Error(`Duplicate project path: ${path}`);
        }
        if (file.size > PROJECT_LIMITS.fileBytes) {
          throw new Error(`${filename} exceeds the per-file project size limit.`);
        }
        if (state.projectFiles.length + loaded.length + 1 > PROJECT_LIMITS.files) {
          throw new Error(`Project exceeds the ${PROJECT_LIMITS.files} file limit.`);
        }
        const content = await file.text();
        const size = new Blob([content]).size;
        if (size > PROJECT_LIMITS.fileBytes) {
          throw new Error(`${filename} exceeds the per-file project size limit.`);
        }
        totalBytes += size;
        if (totalBytes > PROJECT_LIMITS.totalBytes) {
          throw new Error('Project exceeds the total project size limit.');
        }
        loaded.push({ path, content, size });
        existingPaths.add(path.toLowerCase());
      }
      state.projectFiles = [...state.projectFiles, ...loaded];
      state.currentWorkspacePath ||= state.projectFiles[0]?.path || null;
      if (state.projectEntryFile && !state.projectFiles.some((file) => file.path === state.projectEntryFile)) {
        state.projectEntryFile = '';
      }
      renderApp();
      toast(`${loaded.length} project file(s) added`, 'success');
    } catch (error) {
      toast(error.message || 'One or more selected files could not be read.', 'error');
    } finally {
      event.target.value = '';
    }
  });

  const projectUploadZone = document.querySelector('.upload-zone');
  projectUploadZone?.addEventListener('dragover', (event) => {
    event.preventDefault();
    projectUploadZone.classList.add('drag-active');
  });
  projectUploadZone?.addEventListener('dragleave', () => projectUploadZone.classList.remove('drag-active'));
  projectUploadZone?.addEventListener('drop', (event) => {
    event.preventDefault();
    projectUploadZone.classList.remove('drag-active');
    const input = document.getElementById('project-upload-input');
    const transfer = new DataTransfer();
    Array.from(event.dataTransfer?.files || []).forEach((file) => transfer.items.add(file));
    input.files = transfer.files;
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });

  document.getElementById('clear-project-btn')?.addEventListener('click', () => {
    state.projectFiles = [];
    state.projectEntryFile = '';
    state.currentWorkspacePath = null;
    renderApp();
    toast('Project files cleared', 'success');
  });

  document.querySelectorAll('.tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      state.currentTab = tab.dataset.tab;
      renderApp();
    });
  });

  document.getElementById('retry-review-btn')?.addEventListener('click', () => {
    state.reviewResult = null;
    renderApp();
  });
}

function riskClass(value) {
  const normalized = String(value || 'LOW').toUpperCase();
  if (normalized.includes('CRITICAL')) return 'critical';
  if (normalized.includes('HIGH')) return 'high';
  if (normalized.includes('MEDIUM')) return 'medium';
  if (normalized.includes('LOW')) return 'low';
  return 'info';
}

function renderApp() {
  setTheme(state.theme);
  if (!state.session) {
    if (state.route === 'signin') {
      renderAuthView();
    } else if (state.route === 'signup') {
      renderSignupView();
    } else if (state.route === 'forgot') {
      renderForgotView();
    } else {
      state.route = 'signin';
      renderAuthView();
    }
    return;
  }

  renderShell();

  if (!state.reviewsLoaded && !state.reviewsLoading) {
    state.reviewsLoading = true;
    loadPersistedReviews().catch(() => {
      state.reviewsError = 'Unable to load persisted reviews. Check the backend connection.';
      state.reviewsLoaded = true;
    }).finally(() => {
      state.reviewsLoading = false;
      renderApp();
    });
  }

  if (state.route === 'new-review' || state.route === 'workspace') {
    attachReviewPageListeners();
    attachFindingWorkflowListeners();
  }
}

setTheme(state.theme);
renderApp();