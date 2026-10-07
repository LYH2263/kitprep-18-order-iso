<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const rows = ref<any[]>([])
const error = ref('')
const busyId = ref<number | null>(null)

onMounted(async () => { rows.value = await api('/dishes') })

async function remove(id: number) {
  error.value = ''
  if (!confirm('确定删除该出品？若它被任何未作废备料单用到，服务端会整体拒绝并回退。')) return
  busyId.value = id
  try {
    await api('/dishes/' + id, { method: 'DELETE' })
    rows.value = rows.value.filter((r) => r.id !== id)
  } catch (e: any) {
    try { error.value = JSON.parse(e.message).detail || e.message } catch { error.value = e.message }
  } finally {
    busyId.value = null
  }
}
</script>
<template>
  <h1>菜品</h1>
  <p class="sub">中央厨房出品菜品 · 被未作废备料单（任一订单）用到的出品禁止删除</p>
  <p v-if="error" class="kp-page-err">{{ error }}</p>
  <div class="card">
    <table>
      <thead><tr><th>编码</th><th>名称</th><th>单位</th><th></th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id ?? JSON.stringify(r)">
          <td>{{ r.code }}</td><td>{{ r.name }}</td><td>{{ r.portion_unit }}</td>
          <td><button class="btn kp-btn-danger" :disabled="busyId === r.id" @click="remove(r.id)">删除</button></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<style scoped>
.kp-btn-danger { background: var(--kp-bad); border-color: #7e281d; }
.kp-page-err {
  color: #ffb4a8; font-size: 0.82rem; padding: 0.5rem 0.7rem;
  background: rgba(179, 58, 43, 0.22); border: 1px solid var(--kp-bad);
  border-radius: 2px; display: inline-block;
}
</style>
