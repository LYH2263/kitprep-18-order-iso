<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api'
import BomTreePanel from '../components/BomTreePanel.vue'
import { useOrderScope } from '../orderContext'

const data = ref<any>(null)
const shortages = ref<any[]>([])
const error = ref('')
const busy = ref(false)
const ctx = useOrderScope(reload)

async function reload() {
  error.value = ''
  if (ctx.activeId == null) { data.value = null; shortages.value = []; return }
  data.value = await api('/prep/latest?order_id=' + ctx.activeId)
  const res = await api('/prep/shortages?order_id=' + ctx.activeId)
  shortages.value = res.shortages || []
}

async function run() {
  if (ctx.activeId == null || busy.value) return
  busy.value = true
  error.value = ''
  try {
    // 生成只锁当前订单；本单旧单作废，其它订单的单据、缺料贴、占用一律不动
    await api('/prep/run?order_id=' + ctx.activeId, { method: 'POST' })
    await reload()
  } catch (e: any) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

async function voidRun() {
  if (!data.value?.id || ctx.activeId == null) return
  await api(`/prep/${data.value.id}/void?order_id=${ctx.activeId}`, { method: 'POST' })
  await reload()
}
</script>
<template>
  <h1>备料工作台</h1>
  <p class="sub">左定额树（仅本单定额） · 中备料单快照 · 右缺料便利贴 · 全部停在当前订单域</p>
  <div class="kp-actions">
    <button class="btn" :disabled="busy || ctx.activeId == null" @click="run">
      生成备料单<span class="kp-action-scope">（仅 {{ ctx.orders.find(o => o.id === ctx.activeId)?.code ?? '当前订单' }}）</span>
    </button>
    <button v-if="data?.status === 'active'" class="btn kp-btn-ghost" @click="voidRun">作废本单</button>
    <span v-if="error" class="kp-err">{{ error }}</span>
  </div>
  <div class="kp-workbench" style="margin-top:0.85rem">
    <aside class="kp-bom-tree">
      <h2>菜品 / 定额树 · 本单</h2>
      <BomTreePanel :order-id="ctx.activeId" />
    </aside>
    <section class="kp-worksheet" v-if="data">
      <h2>
        备料单 · {{ data.order?.code }} · {{ data.order?.outlet }}
        <span class="kp-run-tag" :class="data.status === 'active' ? 'kp-run-active' : 'kp-run-void'">
          {{ data.status === 'active' ? '生效中 #' + data.id : (data.id ? '已作废 #' + data.id : '尚未生成') }}
        </span>
      </h2>
      <p v-if="!data.id" style="font-size:0.82rem">当前订单还没生成备料单，点「生成备料单」只锁本单；不会自动代生成。</p>
      <p v-else-if="data.status !== 'active'" style="font-size:0.82rem;color:var(--kp-bad)">
        该单已作废，不再占用库存；重新生成会为本订单创建新单。
      </p>
      <table v-if="data.prep_lines?.length">
        <thead><tr><th>原料</th><th>需求</th><th>生成时结存</th><th>单位</th></tr></thead>
        <tbody>
          <tr v-for="l in data.prep_lines" :key="l.ingredient_id">
            <td>{{ l.ingredient_name }}</td><td>{{ l.need_qty }}</td><td>{{ l.stock_qty }}</td><td>{{ l.unit }}</td>
          </tr>
        </tbody>
      </table>
    </section>
    <aside class="kp-shortage-sticky">
      <h2>⚠ 缺料便利贴</h2>
      <div v-for="r in shortages" :key="r.ingredient_id" class="kp-shortage-item">
        <span>{{ r.ingredient_name }}</span>
        <span class="kp-qty">−{{ r.shortage }} {{ r.unit }}</span>
      </div>
      <p v-if="!shortages.length" style="font-size:0.8rem;margin:0.5rem 0 0">
        {{ data?.status === 'active' ? '暂无缺料' : '当前订单没有生效中的备料单' }}
      </p>
    </aside>
  </div>
</template>
<style scoped>
.kp-actions { display: flex; align-items: center; gap: 0.6rem; }
.kp-action-scope { font-size: 0.72rem; font-weight: 400; opacity: 0.75; }
.kp-btn-ghost { background: transparent; color: #f0e6d8; border: 1px solid #a8b0b8; }
.kp-run-tag { font-size: 0.68rem; padding: 0.05rem 0.4rem; border-radius: 2px; margin-left: 0.4rem; vertical-align: middle; }
.kp-run-active { background: var(--kp-ok); color: #f2f7f2; }
.kp-run-void { background: var(--kp-bad); color: #fdf2f0; }
.kp-err { color: #ffb4a8; font-size: 0.8rem; }
</style>
