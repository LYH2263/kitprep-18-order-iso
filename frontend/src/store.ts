import { reactive } from 'vue'
import { api } from './api'

const KEY = 'kp_current_order_id'

/** 当前订单上下文:所有页面的读写都落在 currentId 这张单上。 */
export const orderStore = reactive({
  orders: [] as any[],
  currentId: (Number(localStorage.getItem(KEY)) || null) as number | null,

  async load() {
    this.orders = await api('/orders')
    if (!this.orders.some((o) => o.id === this.currentId)) {
      this.currentId = this.orders.length ? this.orders[0].id : null
    }
    if (this.currentId != null) localStorage.setItem(KEY, String(this.currentId))
  },

  set(id: number) {
    if (id === this.currentId) return
    this.currentId = id
    localStorage.setItem(KEY, String(id))
  },

  get current(): any | null {
    return this.orders.find((o) => o.id === this.currentId) ?? null
  },
})
