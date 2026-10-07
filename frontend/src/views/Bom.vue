<script setup lang="ts">
import BomTreePanel from '../components/BomTreePanel.vue'
import { useOrderScope } from '../orderContext'

const ctx = useOrderScope(() => {})
</script>
<template>
  <h1>BOM 树 · 订单定额</h1>
  <p class="sub">定额树停在当前订单域：改定额只写当前订单的本单定额，不影响基准 BOM 与其它订单</p>
  <div class="kp-bom-tree" style="max-width:520px">
    <h2>菜品 / BOM · 当前订单 {{ ctx.orders.find(o => o.id === ctx.activeId)?.code ?? '' }}</h2>
    <BomTreePanel :order-id="ctx.activeId" />
  </div>
</template>
