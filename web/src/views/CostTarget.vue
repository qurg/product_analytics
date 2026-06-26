<script setup>
import { ref, reactive, onMounted, nextTick, computed, watch } from 'vue'
import * as echarts from 'echarts'
import {
  getCostLanes, getCostTrend, getCostCurrent, getCostLastPeriod, saveCostBatch,
} from '../api'

const biz = ref('海运')           // 海运 / 跨境到仓 / 小包
const sub = ref('')               // 二级筛选: 跨境=运输类型, 小包=线路
const subOptions = ref([])
const isCB = computed(() => biz.value === '跨境到仓')
const isSP = computed(() => biz.value === '小包')
const subLabel = computed(() => (isCB.value ? '运输类型' : ''))
const hasSub = computed(() => isCB.value)  // 仅跨境有二级筛选; 小包直接列3条线路

const trend = ref({ series: [] })
const current = ref({ rows: [] })
const chartEl = ref(null)
let chart = null
const selectedLanes = ref([])
const hasData = computed(() => trend.value.series.some((s) => s.points && s.points.length))

const showEntry = ref(false)
const entry = reactive({ effective_date: '', end_date: '', rows: [] })
const saving = ref(false)
const toast = ref('')
const COLORS = ['#4285F4', '#34A853', '#F29900', '#9334E6', '#EA4335', '#00ACC1',
                '#FF7043', '#26A69A', '#5C6BC0', '#D4E157']

function params() {
  const p = { biz_type: biz.value }
  if (isCB.value) p.transport_type = sub.value
  return p
}

// 切业务线时刷新二级筛选项
async function refreshSub() {
  if (!hasSub.value) { subOptions.value = []; sub.value = ''; return }
  const lanes = await getCostLanes({ biz_type: biz.value })
  const key = isCB.value ? 'transport_type' : 'region'
  subOptions.value = [...new Set(lanes.map((l) => l[key]).filter(Boolean))]
  if (!subOptions.value.includes(sub.value)) sub.value = subOptions.value[0] || ''
}

async function load() {
  trend.value = await getCostTrend(params())
  current.value = await getCostCurrent(params())
  const all = trend.value.series.map((s) => s.lane)
  selectedLanes.value = all.slice(0, all.length > 8 ? 6 : all.length)
  await nextTick()
  renderChart()
}

function renderChart() {
  if (!hasData.value || !chartEl.value) return
  if (!chart) chart = echarts.init(chartEl.value)
  chart.resize()
  const series = trend.value.series
    .filter((s) => selectedLanes.value.includes(s.lane))
    .map((s) => ({ name: s.lane, type: 'line', step: 'end', symbol: 'circle', symbolSize: 4,
                   data: s.points.map((p) => [p.effective_date, p.amount]) }))
  const s0 = trend.value.series[0] || {}
  chart.setOption({
    color: COLORS,
    tooltip: { trigger: 'axis', valueFormatter: (v) => (v == null ? '' : v.toLocaleString()) },
    legend: { data: series.map((s) => s.name), top: 0, type: 'scroll' },
    grid: { left: 60, right: 20, top: 36, bottom: 40 },
    xAxis: { type: 'time' },
    yAxis: { type: 'value', name: `${s0.currency || ''}/${s0.unit || ''}`, scale: true },
    series,
  }, true)
}

function toggleLane(l) {
  const i = selectedLanes.value.indexOf(l)
  if (i >= 0) selectedLanes.value.splice(i, 1); else selectedLanes.value.push(l)
  renderChart()
}

async function openEntry() {
  const lp = await getCostLastPeriod(params())
  entry.effective_date = lp.suggest_effective || ''
  entry.end_date = ''
  entry.rows = lp.rows.map((r) => ({
    lane_id: r.lane_id, lane: r.lane, unit: r.unit, country: r.country,
    region: r.region, note: r.note, last_amount: r.last_amount, amount: r.last_amount,
  }))
  showEntry.value = true; toast.value = ''
}
function carryAll() { entry.rows.forEach((r) => { r.amount = r.last_amount }) }
function onPaste(e, idx) {
  const text = (e.clipboardData || window.clipboardData).getData('text')
  if (!/[\n\t]/.test(text) && text.split(/\s+/).filter(Boolean).length < 2) return
  e.preventDefault()
  text.split(/[\r\n\t]+/).map((x) => x.trim()).filter(Boolean).forEach((n, k) => {
    const row = entry.rows[idx + k]
    if (row) { const v = parseFloat(n.replace(/,/g, '')); if (!isNaN(v)) row.amount = v }
  })
}
const changed = (r) => r.amount != null && r.amount !== '' &&
  (r.last_amount == null || Number(r.amount) !== Number(r.last_amount))
async function saveBatch() {
  if (!entry.effective_date) { toast.value = '请填生效日期'; return }
  saving.value = true
  try {
    const items = entry.rows.filter((r) => r.amount !== '' && r.amount != null)
      .map((r) => ({ lane_id: r.lane_id, amount: Number(r.amount) }))
    const res = await saveCostBatch({ biz_type: biz.value, effective_date: entry.effective_date,
      end_date: entry.end_date || null, items })
    toast.value = `已保存 ${res.saved} 条`; showEntry.value = false; await load()
  } finally { saving.value = false }
}
const fmt = (v) => (v == null ? '—' : Number(v).toLocaleString())

watch(biz, async () => { await refreshSub(); await load() })
watch(sub, () => { if (hasSub.value) load() })
onMounted(async () => { await refreshSub(); await load() })
window.addEventListener('resize', () => chart && chart.resize())
</script>

<template>
  <div class="filters">
    <div class="filter-group"><label>业务线</label>
      <select v-model="biz"><option>海运</option><option>跨境到仓</option><option>小包</option></select>
    </div>
    <div class="filter-group" v-if="hasSub"><label>{{ subLabel }}</label>
      <select v-model="sub"><option v-for="o in subOptions" :key="o" :value="o">{{ o }}</option></select>
    </div>
    <button class="btn" @click="openEntry">＋ 开一期录入</button>
    <span class="spacer" style="margin-left:auto;font-size:12px;color:var(--text3)">目标成本 · 市场价跟踪</span>
  </div>

  <div class="page" style="max-width:none">
    <div class="card" v-if="showEntry" style="margin-bottom:12px;border:1px solid var(--blue)">
      <div class="card-header" style="position:static">
        <h3>开一期目标成本（{{ biz }}<span v-if="hasSub"> · {{ sub }}</span>）</h3>
        <div class="row" style="gap:8px">
          <label style="font-size:13px">生效日期 <input type="date" v-model="entry.effective_date" class="inp" /></label>
          <label style="font-size:13px">结束日期 <input type="date" v-model="entry.end_date" class="inp" /></label>
          <button class="btn btn-ghost" @click="carryAll">全部沿用上期</button>
        </div>
      </div>
      <p style="font-size:12px;color:var(--text3);margin-bottom:8px">
        本期价已预填上期值，只改变化的；可从 Excel 复制一列粘贴；Tab/Enter 逐格跳。<span v-if="isSP">小包录入 all-in 价；揽收/库内/清关见备注。</span>
      </p>
      <table>
        <thead><tr><th>{{ isCB ? '区域' : '线路' }}</th><th>上期价</th><th>{{ isSP ? '本期空运段' : '本期目标成本' }}</th><th></th></tr></thead>
        <tbody>
          <tr v-for="(r, idx) in entry.rows" :key="r.lane_id">
            <td><b>{{ r.lane }}</b> <span style="color:var(--text3);font-size:11px">/{{ r.unit }}</span></td>
            <td style="color:var(--text3)">{{ fmt(r.last_amount) }}</td>
            <td><input type="number" step="0.01" v-model="r.amount" @paste="onPaste($event, idx)"
                   style="width:120px;border:1px solid var(--border);border-radius:4px;padding:6px 8px"
                   :style="changed(r) ? 'border-color:var(--blue);background:var(--blue-bg)' : ''" /></td>
            <td><span v-if="changed(r)" style="color:var(--blue);font-size:12px">改</span></td>
          </tr>
        </tbody>
      </table>
      <div class="row" style="margin-top:12px;gap:8px">
        <button class="btn" :disabled="saving" @click="saveBatch">{{ saving ? '保存中…' : '保存本期' }}</button>
        <button class="btn btn-ghost" @click="showEntry = false">取消</button>
        <span v-if="toast" class="toast ok" style="margin:0">{{ toast }}</span>
      </div>
    </div>

    <div class="card" style="margin-bottom:12px">
      <div class="card-header" style="position:static">
        <h3>目标成本趋势<span v-if="hasSub" style="color:var(--text3);font-size:12px"> · {{ sub }}（点{{ isSP ? 'PD' : '线路' }}加入对比）</span></h3>
        <div class="chips" style="flex-wrap:wrap;max-width:70%;justify-content:flex-end">
          <span v-for="s in trend.series" :key="s.lane" class="chip"
                :class="{ active: selectedLanes.includes(s.lane) }" @click="toggleLane(s.lane)">{{ s.lane }}</span>
        </div>
      </div>
      <div v-show="hasData" ref="chartEl" style="height:340px"></div>
      <div v-if="!hasData" style="height:160px;display:flex;align-items:center;justify-content:center;color:var(--text3);font-size:13px">
        暂无历史目标成本（如空运待询价）。点右上「开一期录入」录入后这里显示趋势。
      </div>
    </div>

    <div class="card">
      <div class="card-header" style="position:static"><h3>当前目标成本 · 环比变动</h3></div>
      <table>
        <thead><tr>
          <th>{{ isCB ? '区域' : '线路' }}</th>
          <th v-if="isSP">国家</th>
          <th v-if="!isSP">目的港</th><th v-if="!isCB && !isSP">船东</th>
          <th>{{ isSP ? '空运段成本' : '当前目标成本' }}</th><th>生效区间</th><th>环比上期</th>
          <th v-if="!isCB && !isSP">起运港费</th>
          <th v-if="isSP">A段/C段(参考)</th>
        </tr></thead>
        <tbody>
          <tr v-for="r in current.rows" :key="(r.lane||'')+(r.dest_ports||'')">
            <td><b>{{ r.lane }}</b></td>
            <td v-if="isSP" style="font-size:12px;color:var(--text3)">{{ r.country }}</td>
            <td v-if="!isSP" style="color:var(--text3);font-size:12px">{{ r.dest_ports }}</td>
            <td v-if="!isCB && !isSP" style="font-size:12px">{{ r.carrier }}</td>
            <td>
              <template v-if="r.amount != null"><b>{{ fmt(r.amount) }}</b> <span style="color:var(--text3);font-size:11px">{{ r.currency }}/{{ r.unit }}</span></template>
              <span v-else style="color:#F29900;font-size:12px">待录入</span>
            </td>
            <td style="font-size:12px;color:var(--text3)">{{ r.effective_date ? (r.effective_date + ' ~ ' + (r.end_date || '')) : '—' }}</td>
            <td :class="r.change_pct > 0 ? 'c-red' : (r.change_pct < 0 ? 'c-green' : '')">
              <template v-if="r.change_pct != null">{{ r.change_pct > 0 ? '▲' : (r.change_pct < 0 ? '▼' : '') }}{{ Math.abs(r.change_pct) }}%
                <span style="color:var(--text3);font-size:11px">(上期 {{ fmt(r.prev_amount) }})</span></template>
              <span v-else style="color:var(--text3)">—</span>
            </td>
            <td v-if="!isCB && !isSP" style="font-size:12px">{{ fmt(r.extra_fee) }}</td>
            <td v-if="isSP" style="font-size:11px;color:var(--text3)">{{ r.note }}</td>
          </tr>
        </tbody>
      </table>
      <p style="font-size:12px;color:var(--text3);margin-top:10px">
        ▲红=涨 / ▼绿=跌（环比上一期）。
        <span v-if="isSP">小包跟踪 all-in 目标成本；揽收/库内/清关见末列。</span>
        <span v-else-if="isCB">跨境到仓海运按 CBM、空运按 kg；空运无历史价可在「开一期录入」补。</span>
        <span v-else>固定属性在主数据维护，录入只填会变的目标成本。</span>
      </p>
    </div>
  </div>
</template>
