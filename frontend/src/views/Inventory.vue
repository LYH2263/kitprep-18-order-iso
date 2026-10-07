<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { api } from '../api'
import { orderStore } from '../store'

const rows = ref<any[]>([])

async function load() {
  if (!orderStore.currentId) return
  rows.value = await api('/inventory?order_id=' + orderStore.currentId)
}

onMounted(async () => {
  await orderStore.load()
  await load()
})
watch(() => orderStore.currentId, load)
</script>

<template>
  <h1>库存</h1>
  <p class="sub">结存不随生成备料单变动 · 占用列为当前订单({{ orderStore.current?.code }})锁定量</p>
  <div class="card">
    <table>
      <thead><tr><th>编码</th><th>名称</th><th>结存</th><th>占用(本单)</th><th>单位</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id ?? JSON.stringify(r)">
          <td>{{ r.code }}</td><td>{{ r.name }}</td><td>{{ r.stock_qty }}</td>
          <td><span class="badge" :class="r.occupied_qty > 0 ? 'badge-warn' : ''">{{ r.occupied_qty }}</span></td>
          <td>{{ r.unit }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
