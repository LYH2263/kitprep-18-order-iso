<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { api } from '../api'
import { orderStore } from '../store'

const tree = ref<any[]>([])
const error = ref('')
const saving = ref<number | null>(null)

async function load() {
  if (!orderStore.currentId) return
  tree.value = await api('/bom/tree?order_id=' + orderStore.currentId)
}

async function save(line: any) {
  if (!orderStore.currentId || saving.value) return
  saving.value = line.line_id
  error.value = ''
  try {
    await api('/bom/' + line.line_id + '?order_id=' + orderStore.currentId, {
      method: 'PUT',
      body: JSON.stringify({ qty_per_portion: Number(line.qty) }),
    })
    await load()
  } catch (e: any) {
    error.value = String(e?.message || e)
  } finally {
    saving.value = null
  }
}

onMounted(async () => {
  await orderStore.load()
  await load()
})
watch(() => orderStore.currentId, load)
</script>

<template>
  <h1>定额树</h1>
  <p class="sub">{{ orderStore.current?.code }} · 每单一棵定额树,改定额只影响当前订单</p>
  <div v-if="error" class="kp-error">{{ error }}</div>
  <div class="kp-bom-tree" style="max-width:460px">
    <h2>菜品 / 定额 · {{ orderStore.current?.code }}</h2>
    <div v-for="d in tree" :key="d.code" class="kp-dish-node">
      <strong>{{ d.dish }}</strong>
      <span style="font-size:0.7rem;color:#8a8078">{{ d.code }}</span>
      <ul>
        <li v-for="c in d.children" :key="c.line_id" style="display:flex;align-items:center;gap:0.4rem">
          <span style="flex:1">{{ c.ingredient }} / {{ c.unit }}</span>
          <input class="kp-qty-input" type="number" step="0.005" min="0" v-model.number="c.qty" />
          <button class="btn-mini" :disabled="saving === c.line_id" @click="save(c)">
            {{ saving === c.line_id ? '…' : '保存' }}
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>
