import { onMounted, reactive, watch } from 'vue'
import { api } from './api'

export interface KitchenOrder {
  id: number
  code: string
  outlet: string
  status: string
}

/**
 * 当前订单域：所有页面共用。
 * 写入口（生成备料单、改定额、作废）一律带 activeId，
 * 切单只是换一个订单域，绝不替当前单执行写操作。
 */
const state = reactive({
  orders: [] as KitchenOrder[],
  activeId: null as number | null,
  loaded: false,
})

const STORAGE_KEY = 'kitprep.activeOrderId'

export async function loadOrders(prefer?: number | null) {
  state.orders = await api('/orders')
  state.loaded = true
  const stored = Number(localStorage.getItem(STORAGE_KEY))
  const wanted = prefer ?? (stored || null)
  const found = wanted && state.orders.find((o) => o.id === wanted)
  if (found) {
    state.activeId = found.id
  } else if (state.orders.length) {
    state.activeId = state.orders[0].id
  } else {
    state.activeId = null
  }
  persist()
}

export function setActiveOrder(id: number) {
  if (!state.orders.find((o) => o.id === id)) return
  state.activeId = id
  persist()
}

function persist() {
  if (state.activeId != null) localStorage.setItem(STORAGE_KEY, String(state.activeId))
}

export function activeOrder() {
  return state
}

export function orderParam() {
  return { order_id: String(state.activeId ?? '') }
}

/** 页面级用法：挂载时确保订单已加载并拉取本单数据；切换当前单后自动重拉。 */
export function useOrderScope(reload: () => void | Promise<void>) {
  const ctx = activeOrder()
  onMounted(async () => {
    if (!ctx.loaded) await loadOrders()
    if (ctx.activeId != null) await reload()
  })
  watch(
    () => ctx.activeId,
    async (id) => {
      if (id != null) await reload()
    },
  )
  return ctx
}

