import MarkdownIt from 'markdown-it'

// AI text may contain markup: keep raw HTML inert and do not load remote images.
const markdown = new MarkdownIt({ html: false, breaks: true, linkify: false })
markdown.renderer.rules.image = (tokens, index, options, env, renderer) =>
  markdown.utils.escapeHtml(renderer.renderInlineAsText(tokens[index]?.children ?? [], options, env))

export function renderMarkdown(content: string) {
  return markdown.render(content)
}
