// Every /api/... request on pelit.vilpponen.fi lands here (Cloudflare Pages Functions).
// The logic lives in server/api.js so the tests can call it without Cloudflare.
import { handle } from '../../server/api.js';

export function onRequest(context) {
  return handle(context.request, context.env);
}
