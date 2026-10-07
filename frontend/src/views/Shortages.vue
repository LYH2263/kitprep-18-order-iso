<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api'
import { useOrderScope } from '../orderContext'

const rows = ref<any[]>([])
const stats = ref<any>({})
const ctx = useOrderScope(load)

async function load() {
  if (ctx.activeId == null) { rows.value = []; return }
  const res = await api('/prep/shortages?order_id=' + ctx.activeId)
  rows.value = res.shortages; stats.value = res.stats
}
</script>
<template>
  <h1>缺料便利贴</h1>
  <p class="sub">shortage = need − stock（仅正数）· 只贴当前订单未作废备料单的缺料</p>
  <div class="kp-shortage-sticky" style="max-width:360px;transform:rotate(-1deg);margin-bottom:1rem">
    <h2>
      ⚠ {{ ctx.orders.find(o => o.id === ctx.activeId)?.code ?? '' }}
      缺料 {{ stats.shortage_count ?? 0 }} · 合计 {{ stats.total_shortage_qty ?? 0 }}
    </h2>
    <div v-for="r in rows" :key="r.ingredient_id" class="kp-shortage-item">
      <span>{{ r.ingredient_name }}</span>
      <span class="kp-qty">−{{ r.shortage }} {{ r.unit }}</span>
    </div>
    <p v-if="!rows.length" style="font-size:0.8rem;margin:0.5rem 0 0">当前订单没有生效备料单或暂无缺料</p>
  </div>
  <div class="card">
    <table>
      <thead><tr><th>原料</th><th>需求</th><th>生成时结存</th><th>缺料</th><th>单位</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.ingredient_id">
          <td>{{ r.ingredient_name }}</td><td>{{ r.need_qty }}</td><td>{{ r.stock_qty }}</td>
          <td><span class="badge badge-bad">{{ r.shortage }}</span></td><td>{{ r.unit }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
