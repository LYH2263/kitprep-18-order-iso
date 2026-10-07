<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api'
import { useOrderScope } from '../orderContext'

const lines = ref<any[]>([])
const ctx = useOrderScope(loadLines)

async function loadLines() {
  if (ctx.activeId == null) { lines.value = []; return }
  lines.value = await api('/orders/' + ctx.activeId + '/lines')
}
</script>
<template>
  <h1>订单芯片</h1>
  <p class="sub">门店要货 · 顶栏选中即当前订单，以下订单行只属于当前订单域</p>
  <div class="kp-worksheet">
    <h2>订单行 · {{ ctx.orders.find(o => o.id === ctx.activeId)?.code ?? '—' }}</h2>
    <table>
      <thead><tr><th>菜品</th><th>份数</th></tr></thead>
      <tbody>
        <tr v-for="l in lines" :key="l.id"><td>{{ l.dish_name }}</td><td>{{ l.portions }}</td></tr>
      </tbody>
    </table>
    <p v-if="!lines.length" style="font-size:0.82rem;margin:0.5rem 0 0">当前订单没有订单行</p>
  </div>
</template>
