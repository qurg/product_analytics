<script setup>
import { ref, onMounted } from 'vue'
import { importActual, importBudget, importWorkbook, getImports } from '../api'

const wbFile = ref(null)
const wbReplace = ref(true)
const wbResult = ref(null)
const actualFile = ref(null)
const actualYear = ref('')
const budgetFile = ref(null)
const budgetCaliber = ref('sign')
const budgetYear = ref(2026)
const logs = ref([])
const toast = ref(null)
const busy = ref(false)

function show(msg, ok = true) {
  toast.value = { msg, ok }
  setTimeout(() => (toast.value = null), 4000)
}

async function refresh() {
  logs.value = await getImports()
}

async function doWorkbook() {
  if (!wbFile.value) return show('请先选择文件', false)
  busy.value = true
  wbResult.value = null
  try {
    const r = await importWorkbook(wbFile.value, wbReplace.value)
    wbResult.value = r.sheets
    const total = r.sheets.reduce((s, x) => s + x.rows, 0)
    show(`工作簿导入成功：${r.sheets.length} 个表 / 共 ${total} 行`)
    await refresh()
  } catch (e) {
    show('导入失败：' + (e.response?.data?.detail || e.message), false)
  } finally {
    busy.value = false
  }
}

async function doActual() {
  if (!actualFile.value) return show('请先选择文件', false)
  busy.value = true
  try {
    const r = await importActual(actualFile.value, actualYear.value || undefined)
    show(`实际数导入成功：${r.rows} 行`)
    await refresh()
  } catch (e) {
    show('导入失败：' + (e.response?.data?.detail || e.message), false)
  } finally {
    busy.value = false
  }
}

async function doBudget() {
  if (!budgetFile.value) return show('请先选择文件', false)
  busy.value = true
  try {
    const r = await importBudget(budgetFile.value, budgetCaliber.value, budgetYear.value)
    show(`预算导入成功：${r.rows} 行`)
    await refresh()
  } catch (e) {
    show('导入失败：' + (e.response?.data?.detail || e.message), false)
  } finally {
    busy.value = false
  }
}

onMounted(refresh)
</script>

<template>
  <div class="page">
    <div class="upload-card" style="border-color:var(--blue)">
      <h3>一键导入汇总工作簿（推荐）</h3>
      <p>直接上传含多个 sheet 的汇总 Excel（如「25-26汇总数据.xlsx」），系统自动识别：含三级产品的表→实际数；签约/操作损益表→对应口径预算。日期列自动取年月，脏值归「未分配」。</p>
      <div class="row">
        <input type="file" accept=".xlsx,.xls" @change="wbFile = $event.target.files[0]" />
        <label style="font-size:13px;color:var(--text2);display:flex;align-items:center;gap:6px">
          <input type="checkbox" v-model="wbReplace" /> 全量覆盖
        </label>
        <button class="btn" :disabled="busy" @click="doWorkbook">一键导入</button>
      </div>
      <table v-if="wbResult" style="margin-top:14px">
        <thead><tr><th>工作表</th><th>识别为</th><th>导入行数</th></tr></thead>
        <tbody>
          <tr v-for="s in wbResult" :key="s.sheet">
            <td>{{ s.sheet }}</td><td>{{ s.kind }}</td><td>{{ s.rows }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="upload-card">
      <h3>导入实际经营数</h3>
      <p>Excel 表头支持中英文，需包含列：<code>年/year</code> <code>月/month</code> <code>洲际/region</code> <code>二级产品/l2</code> <code>三级产品/l3</code> <code>收入/revenue</code> <code>毛利/gross</code> <code>贡献利润/contrib</code>。同维度重复导入将覆盖旧值。</p>
      <div class="row">
        <input type="file" accept=".xlsx,.xls" @change="actualFile = $event.target.files[0]" />
        <input type="number" class="inp" v-model="actualYear" placeholder="缺省年份(可选)" style="width:140px" />
        <button class="btn" :disabled="busy" @click="doActual">导入实际数</button>
      </div>
    </div>

    <div class="upload-card">
      <h3>导入预算</h3>
      <p>表头需包含：<code>月/month</code> <code>洲际/region</code> <code>二级产品/l2</code> <code>收入/revenue</code> <code>毛利/gross</code> <code>贡献利润/contrib</code>。预算按口径与年份分别管理。</p>
      <div class="row">
        <input type="file" accept=".xlsx,.xls" @change="budgetFile = $event.target.files[0]" />
        <select class="inp" v-model="budgetCaliber">
          <option value="sign">签约口径</option>
          <option value="op">操作口径</option>
        </select>
        <input type="number" class="inp" v-model="budgetYear" style="width:100px" />
        <button class="btn" :disabled="busy" @click="doBudget">导入预算</button>
      </div>
    </div>

    <div v-if="toast" class="toast" :class="toast.ok ? 'ok' : 'err'">{{ toast.msg }}</div>

    <div class="upload-card" v-if="logs.length">
      <h3>导入记录</h3>
      <table>
        <thead><tr><th>类型</th><th>文件</th><th>行数</th><th>时间</th></tr></thead>
        <tbody>
          <tr v-for="l in logs" :key="l.id">
            <td>{{ l.kind }}</td><td>{{ l.filename }}</td><td>{{ l.rows }}</td>
            <td>{{ l.created_at?.replace('T', ' ').slice(0, 19) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
