<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { orderStore } from './store'

onMounted(() => orderStore.load())
</script>

<template>
  <div class="kp-kitchen">
    <header class="kp-order-bar">
      <div class="kp-brand">KitPrep · 中央厨房备料台</div>
      <div class="kp-chips" v-if="orderStore.orders.length">
        <button
          v-for="o in orderStore.orders"
          :key="o.id"
          class="kp-chip kp-chip-order"
          :class="{ 'kp-chip-active': o.id === orderStore.currentId }"
          @click="orderStore.set(o.id)"
        >{{ o.code }} · {{ o.outlet }}</button>
      </div>
      <nav class="kp-chips">
        <RouterLink to="/orders" class="kp-chip">订单</RouterLink>
        <RouterLink to="/prep" class="kp-chip">备料单</RouterLink>
        <RouterLink to="/bom" class="kp-chip">定额树</RouterLink>
        <RouterLink to="/dishes" class="kp-chip">出品</RouterLink>
        <RouterLink to="/shortages" class="kp-chip">缺料</RouterLink>
        <RouterLink to="/inventory" class="kp-chip">库存</RouterLink>
      </nav>
    </header>
    <main class="kp-bench">
      <RouterView />
    </main>
  </div>
</template>
