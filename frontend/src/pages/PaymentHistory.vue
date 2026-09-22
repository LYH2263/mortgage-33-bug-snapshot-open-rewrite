<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'
const items = ref([])
const detail = ref(null)
const err = ref('')
const openId = ref(null)
onMounted(async () => { items.value = (await getJSON('/api/history')).items })
const open = async (id) => {
  err.value = ''
  try { detail.value = await getJSON('/api/history/' + id) }
  catch (e) { err.value = `打开 #${id} 失败：${e.message}` }
}
const openByInput = () => { if (openId.value) open(openId.value) }
</script>
<template><div class="page"><h1>试算记录</h1>
<p v-if="err" class="err">{{ err }}</p>
<p><input v-model.number="openId" type="number" min="1" placeholder="编号" /> <button @click="openByInput">按编号打开</button></p>
<table>
<tr><th>编号</th><th>时间</th><th>摘要月供</th><th></th></tr>
<tr v-for="h in items" :key="h.id"><td>#{{ h.id }}</td><td>{{ h.created_at }}</td><td>{{ h.monthly_payment }}</td><td><button @click="open(h.id)">打开</button></td></tr>
</table>
<section v-if="detail">
<h2>记录 #{{ detail.id }}（钉选）</h2>
<p>写入时输入：本金 {{ detail.input.principal }} · 年利率 {{ detail.input.annual_rate }}% · {{ detail.input.months }} 期</p>
<p>月供 {{ detail.monthly_payment }} · 利息合计 {{ detail.total_interest }}</p>
<table>
<tr><th>期</th><th>月供</th><th>本金</th><th>利息</th><th>余额</th></tr>
<tr v-for="r in detail.preview" :key="r.period"><td>第{{ r.period }}期</td><td>{{ r.payment }}</td><td>{{ r.principal }}</td><td>{{ r.interest }}</td><td>{{ r.balance }}</td></tr>
</table>
</section>
</div></template>
<style scoped>.err { color: #a33; }</style>
