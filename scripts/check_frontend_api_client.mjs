import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'

const repoRoot = process.cwd()
const sourceRoot = join(repoRoot, 'frontend', 'src')
const allowedDirectFetchFiles = new Set([
  join(sourceRoot, 'api', 'config.js'),
])
const extensions = new Set(['.js', '.jsx', '.ts', '.tsx'])

const rules = [
  {
    name: 'direct /api fetch',
    pattern: /fetch\s*\(\s*(['"`])\/?api\//,
    allowed: allowedDirectFetchFiles,
  },
  {
    name: 'direct API_BASE_URL usage',
    pattern: /\bAPI_BASE_URL\b/,
    allowed: allowedDirectFetchFiles,
  },
  {
    name: 'axios usage',
    pattern: /\baxios\b/,
    allowed: new Set(),
  },
]

const getExtension = (filePath) => {
  const match = filePath.match(/\.[^.]+$/)
  return match ? match[0] : ''
}

const walk = (dir) => {
  const files = []
  for (const entry of readdirSync(dir)) {
    const fullPath = join(dir, entry)
    const stats = statSync(fullPath)
    if (stats.isDirectory()) {
      files.push(...walk(fullPath))
    } else if (extensions.has(getExtension(fullPath))) {
      files.push(fullPath)
    }
  }
  return files
}

const failures = []

for (const filePath of walk(sourceRoot)) {
  const content = readFileSync(filePath, 'utf8')
  const lines = content.split(/\r?\n/)

  for (const rule of rules) {
    if (rule.allowed.has(filePath)) continue
    lines.forEach((line, index) => {
      if (rule.pattern.test(line)) {
        failures.push({
          rule: rule.name,
          file: relative(repoRoot, filePath),
          line: index + 1,
          text: line.trim(),
        })
      }
    })
  }
}

if (failures.length > 0) {
  console.error('Protected frontend API calls must use frontend/src/api/config.js.')
  for (const failure of failures) {
    console.error(`- ${failure.rule}: ${failure.file}:${failure.line} ${failure.text}`)
  }
  process.exit(1)
}

console.log('Frontend API client check passed: no direct protected /api fetches or axios usage found.')
