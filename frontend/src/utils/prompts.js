export function buildSystemPrompt({ role, memorySummary='', userPrefs={} }){
  const safety = `安全原则：
- 拒绝违法、暴力、成人与仇恨内容；
- 不提供医疗/法律/金融等高风险建议的确定性结论；
- 角色扮演在不提供真实世界可执行的危险指令前提下进行。`

  const consistency = memorySummary ? `对话短期记忆（可用但不要重复背诵）：${memorySummary}` : '无历史摘要。'

  return `${role.system}

${safety}

一致性与记忆：${consistency}

输出要求：
- 正常回答后，追加标记段：
[DEEP_QUESTIONS]
- 1~2 个可深挖问题
[END]`
}