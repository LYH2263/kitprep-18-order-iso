<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { api } from '../api'
import { orderStore } from '../store'

const lines = ref<any[]>([])

async function loadLines() {
  lines.value = orderStore.currentId
    ? await api('/orders/' + orderStore.currentId + '/lines')
    : []
}

onMounted(async () => {
  await orderStore.load()
  await loadLines()
})
watch(() => orderStore.currentId, loadLines)
</script>

<template>
  <h1>订单芯片</h1>
  <p class="sub">门店要货 · 顶栏芯片切换当前订单,全站读写只落在当前订单</p>
  <div class="kp-chips" style="margin-bottom:1rem">
    <button
      v-for="o in orderStore.orders"
      :key="o.id"
      class="kp-chip kp-chip-order"
      :class="{ 'kp-chip-active': o.id === orderStore.currentId }"
      @click="orderStore.set(o.id)"
    >{{ o.code }} · {{ o.outlet }} · {{ o.status }}</button>
  </div>
  <div class="kp-worksheet" v-if="orderStore.current">
    <h2>订单行 · {{ orderStore.current.code }} · {{ orderStore.current.outlet }}</h2>
    <table>
      <thead><tr><th>菜品</th><th>份数</th></tr></thead>
      <tbody>
        <tr v-for="l in lines" :key="l.id"><td>{{ l.dish_name }}</td><td>{{ l.portions }}</td></tr>
      </tbody>
    </table>
  </div>
</template>
