import Anthropic from '@anthropic-ai/sdk'

const SYSTEM_PROMPT = `You are an expert translator of Hebrew Torah literature into Ashkenazi English. Use traditional Ashkenazi transliterations and terminology:
- Shabbos (not Shabbat), Beis HaMikdash (not Bet HaMikdash), davening (not praying), Hashem (not God)
- Use 'the' before Hebrew terms when natural in English
- Maintain the scholarly tone of the original
- Preserve all source references (e.g., pesukim, Gemara references) in their original form
- When translating measurements, keep the Hebrew unit name and add the English equivalent in parentheses
- Do not add explanatory notes unless absolutely necessary for comprehension
Return ONLY the English translation, no commentary.`

let _anthropic: Anthropic | null = null

function getClient(): Anthropic {
  if (!_anthropic) {
    _anthropic = new Anthropic({
      apiKey: process.env["ANTHROPIC_API_KEY"]!,
    })
  }
  return _anthropic
}

export async function translateHebrew({
  hebrewText,
  context,
}: {
  hebrewText: string
  context?: string
}): Promise<string> {
  const client = getClient()

  let userMessage = `Translate the following Hebrew text:\n\n${hebrewText}`
  if (context) {
    userMessage = `Context from surrounding text:\n${context}\n\n${userMessage}`
  }

  const response = await client.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 4096,
    system: SYSTEM_PROMPT,
    messages: [
      {
        role: 'user',
        content: userMessage,
      },
    ],
  })

  const textBlock = response.content.find((block) => block.type === 'text')
  if (!textBlock || textBlock.type !== 'text') {
    throw new Error('No text response from Claude')
  }

  return textBlock.text
}
