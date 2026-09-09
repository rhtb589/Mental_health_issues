const PHQ9_SEVERITY = [
  [0, 4, 'Minimal depression'],
  [5, 9, 'Mild depression'],
  [10, 14, 'Moderate depression'],
  [15, 19, 'Moderately severe depression'],
  [20, 27, 'Severe depression'],
]

const GAD7_SEVERITY = [
  [0, 4, 'Minimal anxiety'],
  [5, 9, 'Mild anxiety'],
  [10, 14, 'Moderate anxiety'],
  [15, 21, 'Severe anxiety'],
]

const PHQ4_SEVERITY = [
  [0, 2, 'Minimal'],
  [3, 5, 'Mild'],
  [6, 8, 'Moderate'],
  [9, 12, 'Severe'],
]

function sumItems(responses: Record<string, number>, ids: string[]): number {
  return ids.reduce((sum, id) => sum + (responses[id] || 0), 0)
}

function interpret(score: number, bands: number[][]): string {
  for (const [low, high, label] of bands) {
    if (score >= low && score <= high) return label as string
  }
  return 'Unknown'
}

function scorePHQ9(responses: Record<string, any>) {
  const ids = Array.from({ length: 9 }, (_, i) => `PHQ9_${String(i + 1).padStart(2, '0')}`)
  const score = sumItems(responses, ids)
  const item9 = responses['PHQ9_09'] || 0
  const safetyFlag = item9 >= 1
  return {
    score,
    interpretation: interpret(score, PHQ9_SEVERITY),
    high_risk: safetyFlag,
    details: { safety_flag: safetyFlag, item_9_score: item9 },
  }
}

function scoreGAD7(responses: Record<string, any>) {
  const ids = Array.from({ length: 7 }, (_, i) => `GAD7_${String(i + 1).padStart(2, '0')}`)
  const score = sumItems(responses, ids)
  return {
    score,
    interpretation: interpret(score, GAD7_SEVERITY),
    high_risk: false,
    details: {},
  }
}

function scorePHQ4(responses: Record<string, any>) {
  const ids = ['PHQ4_01', 'PHQ4_02', 'PHQ4_03', 'PHQ4_04']
  const score = sumItems(responses, ids)
  const anxiety = (responses['PHQ4_01'] || 0) + (responses['PHQ4_02'] || 0)
  const depression = (responses['PHQ4_03'] || 0) + (responses['PHQ4_04'] || 0)
  return {
    score,
    interpretation: interpret(score, PHQ4_SEVERITY),
    high_risk: false,
    details: { anxiety_subscale: anxiety, depression_subscale: depression },
  }
}

function scoreSAFET(responses: Record<string, any>) {
  let ideationLevel = 0
  for (let i = 1; i <= 5; i++) {
    if (responses[`SAFE-T_SI_${i}`] === 'yes') ideationLevel = i
  }
  const hasIntent = ideationLevel >= 4
  const hasPlan = ideationLevel >= 5
  const hasBehavior = responses['SAFE-T_SB'] === 'yes'
  const highRisk = hasIntent || hasPlan || hasBehavior

  let interpretation: string
  if (hasPlan) interpretation = 'High risk: suicidal ideation with plan'
  else if (hasIntent) interpretation = 'High risk: suicidal ideation with intent'
  else if (hasBehavior) interpretation = 'High risk: history of suicidal behavior'
  else if (ideationLevel === 3) interpretation = 'Moderate risk: thoughts with method'
  else if (ideationLevel === 2) interpretation = 'Moderate risk: active suicidal thoughts'
  else if (ideationLevel === 1) interpretation = 'Low-moderate risk: passive ideation'
  else interpretation = 'No current suicidal ideation'

  const riskCount = Object.entries(responses)
    .filter(([k]) => k.startsWith('risk_'))
    .reduce((sum, [, v]) => sum + (Array.isArray(v) ? v.length : 0), 0)
  const protectCount = Object.entries(responses)
    .filter(([k]) => k.startsWith('protect_'))
    .reduce((sum, [, v]) => sum + (Array.isArray(v) ? v.length : 0), 0)

  return {
    score: { ideation_level: ideationLevel, risk_factors: riskCount, protective_factors: protectCount },
    interpretation,
    high_risk: highRisk,
    details: { has_ideation: ideationLevel > 0, has_intent: hasIntent, has_plan: hasPlan, has_behavior: hasBehavior },
  }
}

export function calculateScore(instrumentId: string, responses: Record<string, any>) {
  switch (instrumentId) {
    case 'PHQ9': return scorePHQ9(responses)
    case 'GAD7': return scoreGAD7(responses)
    case 'PHQ4': return scorePHQ4(responses)
    case 'SAFE-T': return scoreSAFET(responses)
    default: throw new Error(`Unknown instrument: ${instrumentId}`)
  }
}
