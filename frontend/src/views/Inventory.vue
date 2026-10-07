<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api'
import { useOrderScope } from '../orderContext'

const rows = ref<any[]>([])
const ctx = useOrderScope(load)

async function load() {
  if (ctx.activeId == null) { rows.value = []; return }
  rows.value = await api('/inventory?order_id=' + ctx.activeId)
}
</script>
<template>
  <h1>库存</h1>
  <p class="sub">
    结存不随备料单扣减，永远停在生成前；「本单占用」只统计当前订单未作废备料单的需求
  </p>
  <div class="card">
    <table>
      <thead>
        <tr><th>编码</th><th>名称</th><th>结存（生成前）</th><th>本单占用</th><th>本单可用</th><th>单位</th></tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id ?? JSON.stringify(r)">
          <td>{{ r.code }}</td><td>{{ r.name }}</td>
          <td>{{ r.stock_qty }}</td>
          <td :class="{ 'badge-bad-text': r.occupied_qty > 0 }">{{ r.occupied_qty }}</td>
          <td>{{ r.available_qty }}</td><td>{{ r.unit }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<style scoped>
.badge-bad-text { color: var(--kp-bad); font-weight: 800; }
</style>
