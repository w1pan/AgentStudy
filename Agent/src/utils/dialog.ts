import type { Directive } from 'vue'

const cleanups = new WeakMap<HTMLElement, () => void>()

/** Keep keyboard focus in a modal and return it to the trigger on close. */
export const vDialog: Directive<HTMLElement, () => void> = {
  mounted(el, binding) {
    const previous = document.activeElement as HTMLElement | null
    const focusable = () => Array.from(el.querySelectorAll<HTMLElement>('*')).filter(node =>
      node.matches('button, input, select, textarea, a[href], [tabindex]') &&
      node.tabIndex >= 0 && !node.matches(':disabled') &&
      !node.hidden && node.getAttribute('aria-hidden') !== 'true' &&
      getComputedStyle(node).display !== 'none' && getComputedStyle(node).visibility !== 'hidden',
    )
    const keydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); binding.value(); return }
      if (event.key !== 'Tab') return
      const nodes = focusable()
      const first = nodes[0]
      const last = nodes[nodes.length - 1]
      if (!first || !last) { event.preventDefault(); return }
      if (event.shiftKey && (document.activeElement === first || !el.contains(document.activeElement))) {
        event.preventDefault(); last.focus()
      } else if (!event.shiftKey && (document.activeElement === last || !el.contains(document.activeElement))) {
        event.preventDefault(); first.focus()
      }
    }
    el.addEventListener('keydown', keydown)
    queueMicrotask(() => { if (el.isConnected) focusable()[0]?.focus() })
    cleanups.set(el, () => {
      el.removeEventListener('keydown', keydown)
      if (previous?.isConnected) previous.focus()
    })
  },
  unmounted(el) { cleanups.get(el)?.(); cleanups.delete(el) },
}
