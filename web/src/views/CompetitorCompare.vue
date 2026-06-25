<script setup>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { getCompetitorDimensions, getCompetitorCarriers, getCompetitorZones, getCompetitorCompare } from '../api'

const dims = reactive({ vendors: [], countries: [], services: [] })
const filters = reactive({ country: '', service: '', carrier: '', zone: '' })
const carriers = ref([])
const zones = ref([])
const data = ref(null)
const loading = ref(false)

const VENDOR_COLOR = { 京东: '#4285F4', '4px': '#9334E6', WINIT: '#F29900', 谷仓: '#34A853' }
const isLastmile = computed(() => filters.service === '尾程派送')
const hasZones = computed(() => zones.value.length > 1 || (zones.value.length === 1 && zones.value[0] !== '统一'))

async function refreshCarriers() {
  if (!isLastmile.value) { carriers.value = []; filters.carrier = ''; zones.value = []; filters.zone = ''; return }
  carriers.value = await getCompetitorCarriers({ country: filters.country, service: filters.service })
  if (!carriers.value.includes(filters.carrier)) filters.carrier = carriers.value[0] || ''
  await refreshZones()
}

async function refreshZones() {
  if (!isLastmile.value || !filters.carrier) { zones.value = []; filters.zone = ''; return }
  zones.value = await getCompetitorZones({ country: filters.country, service: filters.service, carrier: filters.carrier })
  filters.zone = ''  // 默认"全部"，一页展示所有分区
}

async function load() {
  if (!filters.country || !filters.service) return
  if (isLastmile.value && !filters.carrier) return
  loading.value = true
  try {
    const p = { country: filters.country, service: filters.service }
    if (isLastmile.value) {
      p.carrier = filters.carrier
      if (filters.zone) p.zone = filters.zone
    }
    data.value = await getCompetitorCompare(p)
  } finally {
    loading.value = false
  }
}

const fmt = (v) => (v == null ? '—' : Number(v).toLocaleString(undefined, { maximumFractionDigits: 4 }))

watch(() => [filters.country, filters.service], async () => { await refreshCarriers(); load() })
watch(() => filters.carrier, async () => { await refreshZones(); load() })
watch(() => filters.zone, load)

onMounted(async () => {
  Object.assign(dims, await getCompetitorDimensions())
  filters.country = dims.countries.includes('美国') ? '美国' : dims.countries[0] || ''
  filters.service = dims.services.includes('B2C出库') ? 'B2C出库' : dims.services[0] || ''
  await refreshCarriers()
  await refreshZones()
  await load()
})
</script>

<template>
  <div class="filters">
    <div class="filter-group">
      <label>国家/市场</label>
      <select v-model="filters.country">
        <option v-for="c in dims.countries" :key="c" :value="c">{{ c }}</option>
      </select>
    </div>
    <div class="filter-group">
      <label>服务环节</label>
      <select v-model="filters.service">
        <option v-for="s in dims.services" :key="s" :value="s">{{ s }}</option>
      </select>
    </div>
    <div class="filter-group" v-if="isLastmile">
      <label>承运商</label>
      <select v-model="filters.carrier">
        <option v-for="c in carriers" :key="c" :value="c">{{ c }}</option>
      </select>
    </div>
    <div class="filter-group" v-if="isLastmile && hasZones">
      <label>分区Zone</label>
      <select v-model="filters.zone">
        <option value="">全部</option>
        <option v-for="z in zones" :key="z" :value="z">{{ z }}</option>
      </select>
    </div>
    <div class="spacer" style="margin-left:auto;font-size:12px;color:var(--text3)" v-if="data">
      单位：{{ data.unit }}（同币种横比，我司={{ data.our }}）
    </div>
  </div>

  <div class="page" style="max-width:none">
    <div class="card" v-if="data && data.rows.length">
      <div class="card-header">
        <h3>{{ filters.country }} · {{ filters.service }} 竞对价格对比</h3>
        <div class="legend">
          <span v-for="v in data.vendors" :key="v" class="legend-item">
            <span class="legend-dot" :style="{ background: VENDOR_COLOR[v] || '#999' }"></span>{{ v }}
          </span>
        </div>
      </div>
      <table>
        <thead>
          <tr>
            <th v-if="data.multi_zone">分区</th>
            <th>档位</th>
            <th v-for="v in data.vendors" :key="v" :style="{ color: VENDOR_COLOR[v] }">{{ v }}{{ v === data.our ? '(我司)' : '' }}</th>
            <th>最低价方</th>
            <th>我司vs最低</th>
            <th>备注</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in data.rows" :key="(r.zone||'') + r.tier">
            <td v-if="data.multi_zone"><b>{{ r.zone }}</b></td>
            <td>{{ r.tier }}</td>
            <td v-for="v in data.vendors" :key="v"
                :style="r.cheapest === v ? 'background:var(--green-bg)' : ''">
              {{ fmt(r.prices[v]) }}<span v-if="r.mixed_currency && r.prices[v] != null" style="color:var(--text3);font-size:11px"> {{ r.currencies[v] }}</span><span v-if="r.flat && r.flat[v]" title="该承运商为区间统一平价(单档)，已广播到本行" style="color:var(--text3);font-size:10px;margin-left:3px">平价</span>
            </td>
            <td>{{ r.mixed_currency ? '币种不一' : (r.cheapest || '—') }}</td>
            <td :class="r.our_vs_best > 0 ? 'c-red' : 'c-green'">
              {{ r.our_vs_best == null ? '—' : (r.our_vs_best > 0 ? '+' : '') + r.our_vs_best + '%' }}
            </td>
            <td style="color:var(--text3);font-size:12px">{{ r.note }}</td>
          </tr>
        </tbody>
      </table>
      <p style="font-size:12px;color:var(--text3);margin-top:12px">
        绿色=该档最低价；「我司vs最低」为正表示京东比最便宜竞对贵的百分比。仓内：入库/出库按单件重量档，存储按货型首计费档；均同币种内对比。
      </p>
    </div>
    <div class="card" v-else-if="!loading">
      <p style="color:var(--text2)">暂无该组合的数据。</p>
    </div>
  </div>
</template>
