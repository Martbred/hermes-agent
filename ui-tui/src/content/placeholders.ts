import { pick } from '../lib/text.js'

export const PLACEHOLDERS = [
  'Describe your goal, relevant context, and desired result…',
  'Try "explain this codebase"',
  'Try "write a test for…"',
  'Try "review the auth module and make one small, tested improvement"',
  'Try "/help" for commands',
  'Try "fix the lint errors"',
  'Try "how does the config loader work?"'
]

export const PLACEHOLDER = pick(PLACEHOLDERS)
