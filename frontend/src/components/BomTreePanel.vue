<script setup lang="ts">
import { ref, watch } from 'vue'
import { api } from '../api'

const props = defineProps<{ orderId: number | null }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

const tree = ref<any[]>([])
const drafts = ref<Record<string, string>>({})
const busy = ref<number | string | null>(null)
const error = ref('')

function key(dishId: number, ingredientId: number) {
  return dishId + ':' + ingredientId
}

async function load() {
  error.value = ''
  if (props.orderId == null) { tree.value = []; return }
  const res = await api('/bom/tree?order_id=' + props.orderId)
  tree.value = res.tree
  const d: Record<string, string> = {}
  for (const n of res.tree)
    for (const c of n.children) d[key(n.dish_id, c.ingredient_id)] = String(c.qty)
  drafts.value = d
}

watch(() => props.orderId, load, { immediate: true })

async function save(dishId: number, child: any) {
  const qty = Number(drafts.value[key(dishId, child.ingredient_id)])
  if (!Number.isFinite(qty) || qty < 0) { error.value = '定额必须是非负数字'; return }
  busy.value = key(dishId, child.ingredient_id)
  error.value = ''
  try {
    await api('/bom/override?order_id=' + props.orderId, {
      method: 'PUT',
      body: JSON.stringify({ dish_id: dishId, ingredient_id: child.ingredient_id, qty_per_portion: qty }),
    })
    await load()
    emit('changed')
  } catch (e: any) {
    error.value = message(e)
  } finally {
    busy.value = null
  }
}

async function reset(dishId: number, child: any) {
  busy.value = key(dishId, child.ingredient_id)
  error.value = ''
  try {
    await api(`/bom/override?order_id=${props.orderId}&dish_id=${dishId}&ingredient_id=${child.ingredient_id}`,
      { method: 'DELETE' })
    await load()
    emit('changed')
  } catch (e: any) {
    error.value = message(e)
  } finally {
    busy.value = null
  }
}

function message(e: any) {
  try { return JSON.parse(e.message).detail || e.message } catch { return e.message }
}
</script>
<template>
  <div>
    <div v-if="error" class="kp-inline-err">{{ error }}</div>
    <div v-for="d in tree" :key="d.code" class="kp-dish-node">
      <strong>{{ d.dish }}</strong>
      <span style="font-size:0.7rem;color:#8a8078">{{ d.code }}</span>
      <ul>
        <li v-for="c in d.children" :key="c.ingredient_id" :class="{ 'kp-override-row': c.overridden }">
          <span>{{ c.ingredient }} ·</span>
          <input
            v-model="drafts[key(d.dish_id, c.ingredient_id)]"
            type="number" min="0" step="0.01" class="kp-qty-input"
          />
          <span>{{ c.unit }} / 份</span>
          <span v-if="c.overridden" class="kp-override-tag" :title="'基准 ' + c.base_qty">本单定额</span>
          <button class="kp-mini-btn" :disabled="busy === key(d.dish_id, c.ingredient_id)"
                  @click="save(d.dish_id, c)">保存</button>
          <button class="kp-mini-btn" :disabled="busy === key(d.dish_id, c.ingredient_id) || !c.overridden"
                  @click="reset(d.dish_id, c)">恢复基准</button>
        </li>
      </ul>
    </div>
  </div>
</template>
<style scoped>
.kp-qty-input {
  width: 4.2rem; margin: 0 0.25rem; padding: 0.05rem 0.3rem;
  font-size: 0.72rem; border: 1px solid var(--kp-steel); border-radius: 2px;
}
.kp-mini-btn {
  margin-left: 0.25rem; padding: 0.05rem 0.4rem; font-size: 0.68rem;
  border: 1px solid #3a281c; border-radius: 2px; cursor: pointer;
  background: var(--kp-wood-lt); color: #f5ebe0;
}
.kp-mini-btn:disabled { opacity: 0.45; cursor: default; }
.kp-override-row { color: #ffd98a; font-weight: 700; }
.kp-override-tag {
  display: inline-block; margin-left: 0.25rem; padding: 0 0.3rem;
  font-size: 0.62rem; border-radius: 2px;
  background: var(--kp-accent); color: #1c1208; font-weight: 800;
}
.kp-inline-err {
  color: #ffb4a8; font-size: 0.72rem; padding: 0.35rem 0.55rem;
  background: rgba(179, 58, 43, 0.25); border: 1px solid var(--kp-bad);
  margin-bottom: 0.4rem;
}
</style>
