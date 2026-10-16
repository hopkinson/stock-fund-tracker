<template>
  <div v-if="visible" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-md animate-in fade-in duration-200">
    <div class="bg-slate-900/95 border border-slate-800/90 rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl shadow-black/80 flex flex-col max-h-[88vh]">
      
      <!-- 弹窗顶栏 -->
      <div class="px-6 py-4 border-b border-slate-800/80 flex items-center justify-between bg-slate-900/60 shrink-0">
        <div class="flex items-center space-x-3">
          <div class="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
            <BellRing class="w-5 h-5" />
          </div>
          <div>
            <div class="flex items-center space-x-2">
              <h3 class="font-bold text-slate-100 text-base tracking-tight">盘中异动与智能止盈策略</h3>
              <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wide bg-amber-400/10 text-amber-400 border border-amber-400/20">
                支持股票 & ETF
              </span>
            </div>
            <p class="text-xs text-slate-400 mt-0.5">当盘中涨跌或累计收益达到设定目标时，自动通过微信服务号发送提醒</p>
          </div>
        </div>
        <button 
          @click="$emit('close')" 
          class="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-slate-800 transition active:scale-95"
          title="关闭"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- 主体滚动区 -->
      <div class="p-6 space-y-6 overflow-y-auto flex-1 text-slate-200">
        
        <!-- 小白专属：一键快捷模版 -->
        <div class="bg-gradient-to-r from-slate-900 to-slate-800/60 p-4 rounded-xl border border-slate-700/60">
          <div class="flex items-center justify-between mb-2.5">
            <div class="text-xs font-semibold text-slate-300 flex items-center space-x-1.5">
              <Sparkles class="w-3.5 h-3.5 text-amber-400" />
              <span>小白一键快速模版 (点击自动填充)</span>
            </div>
            <span class="text-[11px] text-slate-400">免手动计算阈值，省心省力</span>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <button 
              type="button"
              v-for="preset in presets" 
              :key="preset.title"
              @click="applyPreset(preset)"
              class="p-2.5 rounded-lg border text-left transition group active:scale-[0.98] flex flex-col justify-between"
              :class="activePresetTitle === preset.title ? 'bg-amber-500/10 border-amber-500/40 text-amber-300' : 'bg-slate-850/80 border-slate-750/70 hover:border-slate-600 text-slate-300'"
            >
              <div>
                <div class="flex items-center justify-between">
                  <span class="text-xs font-bold">{{ preset.title }}</span>
                  <span class="text-[10px] font-mono px-1 rounded" :class="preset.badgeClass">{{ preset.valText }}</span>
                </div>
                <div class="text-[11px] text-slate-400 mt-1 line-clamp-1 leading-snug">{{ preset.desc }}</div>
              </div>
            </button>
          </div>
        </div>

        <!-- 新建监控策略表单 -->
        <form @submit.prevent="handleAddRule" class="bg-slate-950/70 p-4.5 rounded-xl border border-slate-800 space-y-3.5">
          <div class="flex items-center justify-between">
            <div class="text-xs font-semibold text-slate-200 flex items-center space-x-1.5">
              <PlusCircle class="w-3.5 h-3.5 text-slate-400" />
              <span>新建监控策略</span>
            </div>
            <!-- ETF 友好贴士 -->
            <div v-if="selectedIsEtf" class="text-[11px] text-sky-400 flex items-center space-x-1 bg-sky-950/40 px-2 py-0.5 rounded border border-sky-800/50">
              <ShieldCheck class="w-3 h-3 text-sky-400" />
              <span>ETF标的：建议重点配置“低吸补仓(-2%)”或“目标止盈(+15%)”</span>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-12 gap-2.5">
            <!-- 1. 标的选择 -->
            <div class="sm:col-span-5">
              <label class="block text-[11px] text-slate-400 mb-1">选择监控标的 (股票 / ETF / 基金)</label>
              <select 
                v-model="newRule.code" 
                @change="onSelectPosition" 
                class="w-full bg-slate-800 border border-slate-700 text-slate-100 text-xs rounded-xl px-3 py-2.5 focus:outline-none focus:border-amber-500 transition cursor-pointer"
                required
              >
                <option value="" disabled>点击选择持仓标的...</option>
                <option v-for="p in positions" :key="p.id" :value="p.code">
                  {{ isEtfCode(p.code, p.name) ? '[ETF/基金] ' : '[股票] ' }}{{ p.name }} ({{ p.code }})
                </option>
              </select>
            </div>

            <!-- 2. 规则类型 -->
            <div class="sm:col-span-4">
              <label class="block text-[11px] text-slate-400 mb-1">监控触发条件</label>
              <select 
                v-model="newRule.rule_type" 
                class="w-full bg-slate-800 border border-slate-700 text-slate-100 text-xs rounded-xl px-3 py-2.5 focus:outline-none focus:border-amber-500 transition cursor-pointer"
              >
                <option value="stop_profit">🎯 累计收益达到 (止盈线)</option>
                <option value="day_change_below">📉 今日盘中跌超 (低吸提醒)</option>
                <option value="day_change_above">📈 今日盘中涨超 (暴涨提醒)</option>
                <option value="stop_loss">🛡️ 累计亏损达到 (止损线)</option>
              </select>
            </div>

            <!-- 3. 阈值与添加按钮 -->
            <div class="sm:col-span-3">
              <label class="block text-[11px] text-slate-400 mb-1">触发百分比 (%)</label>
              <div class="flex items-center space-x-2">
                <div class="relative flex-1">
                  <input 
                    v-model.number="newRule.threshold" 
                    type="number" 
                    step="0.1" 
                    min="0.1"
                    placeholder="如: 15.0" 
                    class="w-full bg-slate-800 border border-slate-700 text-slate-100 text-xs rounded-xl pl-3 pr-6 py-2.5 font-mono focus:outline-none focus:border-amber-500 transition"
                    required
                  />
                  <span class="absolute right-2.5 top-2.5 text-xs text-slate-400 pointer-events-none">%</span>
                </div>
                <button 
                  type="submit" 
                  class="px-3.5 py-2.5 text-xs font-semibold bg-amber-600 hover:bg-amber-500 active:scale-95 text-white rounded-xl transition shadow-lg shadow-amber-600/20 shrink-0"
                >
                  添加
                </button>
              </div>
            </div>
          </div>
        </form>

        <!-- 现存规则列表 -->
        <div class="space-y-2.5">
          <div class="flex items-center justify-between">
            <div class="text-xs font-semibold text-slate-400 flex items-center space-x-1.5">
              <span>已生效监控清单</span>
              <span class="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-800 text-slate-400 border border-slate-700 font-mono">
                {{ rules.length }}
              </span>
            </div>
            <span class="text-[11px] text-slate-500">交易时间内每 20 秒毫秒级刷新检测</span>
          </div>

          <!-- 规则卡片容器 -->
          <div class="space-y-2">
            <div 
              v-for="rule in rules" 
              :key="rule.id" 
              class="p-3.5 bg-slate-850/60 hover:bg-slate-800/60 rounded-xl border border-slate-750/70 hover:border-slate-700 flex items-center justify-between text-xs transition duration-150"
            >
              <div class="flex items-center space-x-3">
                <span 
                  class="px-1.5 py-0.5 rounded text-[10px] font-medium"
                  :class="isEtfCode(rule.code, rule.name) ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20' : 'bg-slate-700/40 text-slate-300 border border-slate-600/30'"
                >
                  {{ isEtfCode(rule.code, rule.name) ? 'ETF/基金' : '股票' }}
                </span>
                
                <div>
                  <div class="flex items-center space-x-2">
                    <span class="font-bold text-slate-200 text-sm">{{ rule.name }}</span>
                    <span class="text-slate-400 font-mono text-[11px]">{{ rule.code }}</span>
                  </div>
                </div>
              </div>

              <div class="flex items-center space-x-3">
                <!-- 规则状态 Badge -->
                <div class="px-2.5 py-1 rounded-lg text-xs font-medium font-mono flex items-center space-x-1" :class="getRuleBadge(rule.rule_type)">
                  <span>{{ formatRuleText(rule) }}</span>
                </div>

                <!-- 删除按钮 -->
                <button 
                  @click="deleteRule(rule.id)" 
                  class="text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 p-1.5 rounded-lg transition active:scale-95"
                  title="移除此预警"
                >
                  <Trash2 class="w-4 h-4" />
                </button>
              </div>
            </div>

            <!-- 空列表占位 -->
            <div v-if="rules.length === 0" class="py-10 text-center rounded-xl border border-dashed border-slate-800 bg-slate-900/30">
              <div class="w-10 h-10 rounded-full bg-slate-800/80 flex items-center justify-center mx-auto text-slate-500 mb-2">
                <BellOff class="w-5 h-5" />
              </div>
              <p class="text-xs font-medium text-slate-400">暂未配置任何预警策略</p>
              <p class="text-[11px] text-slate-500 mt-1">选择上方标的并点击“小白快捷模版”，即可轻松添加</p>
            </div>
          </div>
        </div>

      </div>

      <!-- 弹窗底栏 -->
      <div class="px-6 py-3.5 border-t border-slate-800 bg-slate-950/80 flex items-center justify-between text-xs text-slate-400 shrink-0">
        <div class="flex items-center space-x-2">
          <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>监控引擎运行中：触发后微信立即通知，同一标的 1 小时内不重复打扰</span>
        </div>
        <button 
          @click="$emit('close')" 
          class="px-4 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 transition active:scale-95 text-xs"
        >
          完成
        </button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { BellRing, BellOff, X, Trash2, PlusCircle, Sparkles, ShieldCheck } from 'lucide-vue-next'
import { getAlertRules, createAlertRule, deleteAlertRule } from '../api'

const props = defineProps({
  visible: Boolean,
  positions: {
    type: Array,
    default: () => []
  }
})

const rules = ref([])
const activePresetTitle = ref('')

const newRule = ref({
  code: '',
  name: '',
  rule_type: 'stop_profit',
  threshold: 15.0,
  enabled: true
})

// 小白快捷预设模版列表
const presets = [
  {
    title: '稳健止盈',
    valText: '+15%',
    rule_type: 'stop_profit',
    threshold: 15.0,
    desc: '达标落袋为安，防止盈利坐过山车',
    badgeClass: 'bg-rose-500/20 text-rose-300'
  },
  {
    title: '高抛止盈',
    valText: '+25%',
    rule_type: 'stop_profit',
    threshold: 25.0,
    desc: '适合高弹性行业/牛市收益收割',
    badgeClass: 'bg-rose-500/20 text-rose-300'
  },
  {
    title: '低吸补仓',
    valText: '跌 -2%',
    rule_type: 'day_change_below',
    threshold: 2.0,
    desc: '大盘/ETF回调提醒，适合定投扣款',
    badgeClass: 'bg-emerald-500/20 text-emerald-300'
  },
  {
    title: '严格止损',
    valText: '-8%',
    rule_type: 'stop_loss',
    threshold: 8.0,
    desc: '个股回撤控制，避免越陷越深',
    badgeClass: 'bg-amber-500/20 text-amber-300'
  }
]

// 判断标的是否为 ETF、指数基金或 LOF
const isEtfCode = (code, name = '') => {
  if (!code) return false
  const c = String(code).trim()
  const n = String(name || '')
  if (c.startsWith('51') || c.startsWith('15') || c.startsWith('16') || c.startsWith('58')) return true
  if (n.includes('ETF') || n.includes('指数') || n.includes('LOF') || n.includes('联接')) return true
  return false
}

const selectedIsEtf = computed(() => {
  return isEtfCode(newRule.value.code, newRule.value.name)
})

const fetchRules = async () => {
  try {
    const res = await getAlertRules()
    rules.value = res.data || []
  } catch (e) {
    console.error(e)
  }
}

const onSelectPosition = () => {
  const p = props.positions.find(item => item.code === newRule.value.code)
  if (p) {
    newRule.value.name = p.name
    // 如果是 ETF，默认切换为更适合的稳健止盈或补仓
    if (isEtfCode(p.code, p.name) && newRule.value.rule_type === 'stop_loss') {
      newRule.value.rule_type = 'stop_profit'
      newRule.value.threshold = 15.0
    }
  }
}

// 应用小白预设
const applyPreset = (preset) => {
  activePresetTitle.value = preset.title
  newRule.value.rule_type = preset.rule_type
  newRule.value.threshold = preset.threshold
}

const handleAddRule = async () => {
  if (!newRule.value.code) {
    alert('请先选择需要监控的持仓标的')
    return
  }
  if (!newRule.value.name) onSelectPosition()
  try {
    await createAlertRule(newRule.value)
    newRule.value.code = ''
    newRule.value.name = ''
    activePresetTitle.value = ''
    await fetchRules()
  } catch (e) {
    alert('添加规则失败: ' + e.message)
  }
}

const deleteRule = async (id) => {
  try {
    await deleteAlertRule(id)
    await fetchRules()
  } catch (e) {
    alert('删除失败: ' + e.message)
  }
}

const formatRuleText = (r) => {
  const map = {
    day_change_above: `日涨超 +${r.threshold}%`,
    day_change_below: `日跌超 -${r.threshold}%`,
    stop_profit: `止盈线 +${r.threshold}%`,
    stop_loss: `止损线 -${r.threshold}%`
  }
  return map[r.rule_type] || `阈值: ${r.threshold}%`
}

const getRuleBadge = (type) => {
  if (type === 'day_change_above' || type === 'stop_profit') {
    return 'bg-rose-500/10 text-rose-400 border border-rose-500/25'
  }
  if (type === 'day_change_below') {
    return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/25'
  }
  return 'bg-amber-500/10 text-amber-400 border border-amber-500/25'
}

onMounted(() => {
  fetchRules()
})
</script>
