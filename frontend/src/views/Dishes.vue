<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'

const rows = ref<any[]>([])
const error = ref('')

async function load() {
  rows.value = await api('/dishes')
}

async function remove(d: any) {
  error.value = ''
  try {
    await api('/dishes/' + d.id, { method: 'DELETE' })
    await load()
  } catch (e: any) {
    // 被未作废备料单占用时后端返回 409,这里展示原因,单和树都保持原样
    error.value = `${d.name}:删除失败 — ${String(e?.message || e)}`
  }
}

onMounted(load)
</script>

<template>
  <h1>出品</h1>
  <p class="sub">中央厨房出品菜品 · 被未作废备料单用到的出品不可删除</p>
  <div v-if="error" class="kp-error">{{ error }}</div>
  <div class="card">
    <table>
      <thead><tr><th>编码</th><th>名称</th><th>单位</th><th></th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id ?? JSON.stringify(r)">
          <td>{{ r.code }}</td><td>{{ r.name }}</td><td>{{ r.portion_unit }}</td>
          <td><button class="btn-mini danger" @click="remove(r)">删除</button></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
