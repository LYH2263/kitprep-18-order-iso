<script setup lang="ts">
import { onMounted } from 'vue'
import { activeOrder, loadOrders, setActiveOrder } from '../orderContext'

const emit = defineEmits<{ (e: 'change', id: number): void }>()
const ctx = activeOrder()
onMounted(async () => {
  if (!ctx.loaded) await loadOrders()
})
function pick(id: number) {
  setActiveOrder(id)
  emit('change', id)
}
</script>
<template>
  <div class="kp-chips kp-order-switch">
    <span
      v-for="o in ctx.orders"
      :key="o.id"
      class="kp-chip"
      :class="{ 'kp-chip-active': o.id === ctx.activeId }"
      style="cursor:pointer"
      @click="pick(o.id)"
    >
      {{ o.code }} · {{ o.outlet }} · {{ o.status }}
    </span>
    <span v-if="!ctx.orders.length" class="kp-chip">暂无订单</span>
  </div>
</template>
<style scoped>
.kp-order-switch .kp-chip-active {
  background: var(--kp-accent);
  color: #1c1208;
  font-weight: 800;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.3), 0 0 0 2px rgba(196, 122, 44, 0.45);
}
</style>
