const apiOverride = window.CODE_REVIEW_API_URL;
const apiHost = window.location.hostname || '127.0.0.1';
const apiProtocol = window.location.protocol === 'file:' ? 'http:' : window.location.protocol;

window.CODE_REVIEW_CONFIG = {
  apiBaseUrl: apiOverride || `${apiProtocol}//${apiHost}:8000/api`,
  maxCodeChars: 250000,
  maxProjectFiles: 100,
  maxProjectFileBytes: 250000,
  maxProjectTotalBytes: 2000000,
  maxProjectPathChars: 512,
  maxProjectFilenameChars: 255,
  maxProjectContextChars: 50000,
  maxProjectRelatedFileChars: 12000,
  requestTimeoutMs: 300000,
};