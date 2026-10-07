<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { api } from '../api'
import { orderStore } from '../store'

const rows = ref<any[]>([])
const stats = ref<any>({})

async function load() {
  if (!orderStore.currentId) return
  const res = await api('/prep/shortages?order_id=' + orderStore.currentId)
  rows.value = res.shortages
  stats.value = res.stats
}

onMounted(async () => {
  await orderStore.load()
  await load()
})
watch(() => orderStore.currentId, load)
</script>

<template>
  <h1>缺料便利贴</h1>
  <p class="sub">{{ orderStore.current?.code }} · shortage = need − stock(仅正数)· 只看当前订单</p>
  <div class="kp-shortage-sticky" style="max-width:360px;transform:rotate(-1deg);margin-bottom:1rem">
    <h2>⚠ 缺料 {{ stats.shortage_count || 0 }} · 合计 {{ stats.total_shortage_qty || 0 }}</h2>
    <div v-for="r in rows" :key="r.ingredient_id" class="kp-shortage-item">
      <span>{{ r.ingredient_name }}</span>
      <span class="kp-qty">−{{ r.shortage }} {{ r.unit }}</span>
    </div>
    <p v-if="!rows.length" style="font-size:0.8rem;margin:0.5rem 0 0">本单暂无缺料</p>
  </div>
  <div class="card" v-if="rows.length">
    <table>
      <thead><tr><th>原料</th><th>需求</th><th>库存</th><th>缺料</th><th>单位</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.ingredient_id">
          <td>{{ r.ingredient_name }}</td><td>{{ r.need_qty }}</td><td>{{ r.stock_qty }}</td>
          <td><span class="badge badge-bad">{{ r.shortage }}</span></td><td>{{ r.unit }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
