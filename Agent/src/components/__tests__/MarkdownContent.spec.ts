import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import MarkdownContent from '../MarkdownContent.vue'
import AdviceDrawer from '../AdviceDrawer.vue'

describe('advice markdown', () => {
  it('renders emphasis, ordered and nested lists without exposing markdown markers', () => {
    const wrapper = mount(MarkdownContent, { props: { content: '下一餐：**正常吃、补足结构**。\n\n1. 蔬菜\n2. 主食\n   - 米饭\n   - 面条\n\n`示例`' } })
    expect(wrapper.get('strong').text()).toBe('正常吃、补足结构')
    expect(wrapper.findAll('ol > li')).toHaveLength(2)
    expect(wrapper.findAll('ol ul > li')).toHaveLength(2)
    expect(wrapper.get('code').text()).toBe('示例')
    expect(wrapper.text()).not.toContain('**')
    wrapper.unmount()
  })

  it('reparses incomplete streamed text as more content arrives', async () => {
    const wrapper = mount(MarkdownContent, { props: { content: '建议 **保持' } })
    expect(wrapper.text()).toContain('保持')
    await wrapper.setProps({ content: '建议 **保持均衡**。\n\n- 蔬菜\n- 主食' })
    expect(wrapper.get('strong').text()).toBe('保持均衡')
    expect(wrapper.findAll('li')).toHaveLength(2)
    expect(wrapper.text()).not.toContain('**')
    wrapper.unmount()
  })

  it('escapes raw HTML, rejects executable links, and does not load remote images', () => {
    const content = '<script>alert(1)</script>\n\n<img src=x onerror=alert(1)>\n\n[危险](javascript:alert(1))\n\n[编码](javascript&#58;alert(1))\n\n![图片](https://example.com/track.png)\n\n[正常链接](https://example.com)\n\n```html\n<button onclick="alert(1)">文字</button>\n```'
    const wrapper = mount(MarkdownContent, { props: { content } })
    expect(wrapper.find('script, img, button, iframe').exists()).toBe(false)
    expect(wrapper.findAll('a')).toHaveLength(1)
    expect(wrapper.get('a').attributes('href')).toBe('https://example.com')
    expect(wrapper.get('pre code').text()).toContain('<button onclick=')
    wrapper.unmount()
  })

  it('formats the advice and assistant response while keeping the user message literal', () => {
    const wrapper = mount(AdviceDrawer, { props: {
      card: { type: 'next_meal', title: '下一餐', body: '保持**均衡**', bullets: ['搭配**蔬菜**'] },
      messages: [{ role: 'user', content: '**下一餐**注意什么？' }, { role: 'assistant', content: '**正常吃**。\n\n- 主食\n- 蔬菜' }],
    } })
    expect(wrapper.findAll('.card-context strong')).toHaveLength(2)
    expect(wrapper.get('.message--assistant strong').text()).toBe('正常吃')
    expect(wrapper.findAll('.message--assistant li')).toHaveLength(2)
    expect(wrapper.get('.message--user').text()).toBe('**下一餐**注意什么？')
    expect(wrapper.find('.message--user strong').exists()).toBe(false)
    wrapper.unmount()
  })
})
