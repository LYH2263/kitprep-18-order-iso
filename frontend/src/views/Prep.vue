<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { api } from '../api'
import { orderStore } from '../store'

const tree = ref<any[]>([])
const data = ref<any>(null)
const shortages = ref<any[]>([])
const runs = ref<any[]>([])
const busy = ref(false)
const error = ref('')

async function loadAll() {
  if (!orderStore.currentId) return
  const id = orderStore.currentId
  const [t, latest, s, r] = await Promise.all([
    api('/bom/tree?order_id=' + id),
    api('/prep/latest?order_id=' + id),
    api('/prep/shortages?order_id=' + id),
    api('/prep/runs?order_id=' + id),
  ])
  tree.value = t
  data.value = latest
  shortages.value = s.shortages || []
  runs.value = r
}

async function run() {
  if (!orderStore.currentId || busy.value) return
  busy.value = true
  error.value = ''
  try {
    await api('/prep/run?order_id=' + orderStore.currentId, { method: 'POST' })
    await loadAll()
  } catch (e: any) {
    error.value = String(e?.message || e)
  } finally {
    busy.value = false
  }
}

async function voidRun(runId: number) {
  error.value = ''
  try {
    await api(`/prep/runs/${runId}/void?order_id=` + orderStore.currentId, { method: 'POST' })
    await loadAll()
  } catch (e: any) {
    error.value = String(e?.message || e)
  }
}

onMounted(async () => {
  await orderStore.load()
  await loadAll() // 只读本单现状,不自动生成
})
watch(() => orderStore.currentId, loadAll)
</script>

<template>
  <h1>备料工作台</h1>
  <p class="sub">
    当前订单:{{ orderStore.current?.code }} · {{ orderStore.current?.outlet }} ·
    生成只锁本单,库存结存不动
  </p>
  <div v-if="error" class="kp-error">{{ error }}</div>
  <button class="btn" :disabled="busy || !orderStore.currentId" @click="run">
    {{ busy ? '生成中…' : '生成备料单' }}
  </button>
  <div class="kp-workbench" style="margin-top:0.85rem">
    <aside class="kp-bom-tree">
      <h2>本单定额树</h2>
      <div v-for="d in tree" :key="d.code" class="kp-dish-node">
        <strong>{{ d.dish }}</strong>
        <span style="font-size:0.7rem;color:#8a8078">{{ d.code }}</span>
        <ul>
          <li v-for="(c,i) in d.children" :key="i">{{ c.ingredient }} · {{ c.qty }} {{ c.unit }}</li>
        </ul>
      </div>
    </aside>
    <section class="kp-worksheet" v-if="data">
      <h2>备料单 · {{ data.order?.code }} · {{ data.order?.outlet }}</h2>
      <p v-if="!data.id" class="muted" style="font-size:0.82rem">本单还没有生效备料单,点「生成备料单」。</p>
      <template v-else>
        <table>
          <thead><tr><th>原料</th><th>需求</th><th>库存</th><th>占用</th><th>单位</th></tr></thead>
          <tbody>
            <tr v-for="l in data.prep_lines" :key="l.ingredient_id">
              <td>{{ l.ingredient_name }}</td><td>{{ l.need_qty }}</td><td>{{ l.stock_qty }}</td>
              <td><span class="badge badge-warn">{{ l.occupied_qty }}</span></td><td>{{ l.unit }}</td>
            </tr>
          </tbody>
        </table>
        <h2 style="margin-top:0.9rem">历史备料单</h2>
        <table>
          <thead><tr><th>#</th><th>时间</th><th>状态</th><th></th></tr></thead>
          <tbody>
            <tr v-for="r in runs" :key="r.id">
              <td>{{ r.id }}</td><td>{{ r.created_at }}</td>
              <td>
                <span class="badge" :class="r.status === 'active' ? 'badge-ok' : 'badge-bad'">
                  {{ r.status === 'active' ? '生效' : '已作废' }}
                </span>
              </td>
              <td>
                <button v-if="r.status === 'active'" class="btn-mini danger" @click="voidRun(r.id)">作废</button>
              </td>
            </tr>
          </tbody>
        </table>
      </template>
    </section>
    <aside class="kp-shortage-sticky">
      <h2>⚠ 缺料便利贴</h2>
      <div v-for="r in shortages" :key="r.ingredient_id" class="kp-shortage-item">
        <span>{{ r.ingredient_name }}</span>
        <span class="kp-qty">−{{ r.shortage }} {{ r.unit }}</span>
      </div>
      <p v-if="!shortages.length" style="font-size:0.8rem;margin:0.5rem 0 0">暂无缺料</p>
    </aside>
  </div>
</template>
