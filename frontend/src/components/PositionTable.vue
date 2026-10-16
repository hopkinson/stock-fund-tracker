<template>
  <div class="fin-glow-card bg-[#0e1626]/90 border border-slate-800/80 rounded-2xl overflow-hidden shadow-sm">
    <!-- 列表控制与筛选工具栏 -->
    <div class="p-3.5 sm:p-4 border-b border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <!-- 平台筛选标签 + 标的计数 -->
      <div class="flex items-center space-x-1.5 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
        <button 
          v-for="tab in platformTabsWithCount" 
          :key="tab.value"
          @click="currentPlatform = tab.value"
          class="px-3 py-1.5 text-xs font-medium rounded-lg transition-all shrink-0 flex items-center space-x-1.5"
          :class="currentPlatform === tab.value 
            ? 'bg-indigo-600 text-white shadow-sm font-semibold' 
            : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700/80 hover:text-white border border-slate-700/40'"
        >
          <span>{{ tab.label }}</span>
          <span 
            class="px-1.5 py-0.2 rounded-full text-[10px] num-font"
            :class="currentPlatform === tab.value ? 'bg-indigo-700 text-white' : 'bg-slate-900 text-slate-400'"
          >
            {{ tab.count }}
          </span>
        </button>

        <a 
          v-if="currentPlatform !== 'all'"
          :href="getPlatformUrl(currentPlatform)"
          target="_blank"
          rel="noopener noreferrer"
          class="px-2.5 py-1.5 text-xs font-medium rounded-lg bg-indigo-950/40 hover:bg-indigo-900/60 text-indigo-300 hover:text-indigo-200 border border-indigo-700/40 transition flex items-center space-x-1 shrink-0 ml-1"
          :title="'前往 ' + getPlatformName(currentPlatform) + ' 官网/交易端'"
        >
          <span>打开{{ getPlatformName(currentPlatform) }}</span>
          <ExternalLink class="w-3 h-3" />
        </a>
      </div>

      <!-- 搜索 & 类型筛选 -->
      <div class="flex items-center space-x-2">
        <select 
          v-model="currentType" 
          class="bg-slate-900/90 border border-slate-700/70 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500 font-medium"
        >
          <option value="all">全部类型</option>
          <option value="stock">股票 / ETF</option>
          <option value="fund">基金</option>
        </select>

        <div class="relative flex-1 sm:w-52">
          <input 
            v-model="searchKeyword"
            type="text" 
            placeholder="搜索名称或代码..." 
            class="w-full bg-slate-900/90 border border-slate-700/70 text-slate-200 text-xs rounded-lg pl-7 pr-7 py-1.5 placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-medium"
          />
          <Search class="w-3.5 h-3.5 text-slate-400 absolute left-2 top-2" />
          <button 
            v-if="searchKeyword" 
            @click="searchKeyword = ''"
            class="absolute right-2 top-2 text-slate-500 hover:text-slate-300"
          >
            <X class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>

    <!-- 表格视图 (桌面端) -->
    <div class="hidden md:block overflow-x-auto">
      <table class="w-full text-left text-xs">
        <thead class="bg-[#0b101c] text-slate-400 border-b border-slate-800 font-medium select-none">
          <tr>
            <th class="py-3 px-4">名称 / 代码</th>
            <th class="py-3 px-3 text-center">平台</th>
            <th 
              @click="toggleSort('current_price')"
              class="py-3 px-3 text-right cursor-pointer hover:text-slate-200 transition"
            >
              <div class="flex items-center justify-end space-x-1">
                <span>最新价</span>
                <component :is="getSortIcon('current_price')" class="w-3 h-3 text-slate-500" />
              </div>
            </th>
            <th 
              @click="toggleSort('today_profit_rate')"
              class="py-3 px-3 text-right cursor-pointer hover:text-slate-200 transition"
            >
              <div class="flex items-center justify-end space-x-1">
                <span>今日涨跌</span>
                <component :is="getSortIcon('today_profit_rate')" class="w-3 h-3 text-slate-500" />
              </div>
            </th>
            <th class="py-3 px-3 text-right">持仓数量</th>
            <th class="py-3 px-3 text-right">成本价</th>
            <th 
              @click="toggleSort('market_value')"
              class="py-3 px-3 text-right cursor-pointer hover:text-slate-200 transition"
            >
              <div class="flex items-center justify-end space-x-1">
                <span>市值</span>
                <component :is="getSortIcon('market_value')" class="w-3 h-3 text-slate-500" />
              </div>
            </th>
            <th 
              @click="toggleSort('today_profit')"
              class="py-3 px-3 text-right cursor-pointer hover:text-slate-200 transition"
            >
              <div class="flex items-center justify-end space-x-1">
                <span>今日盈亏</span>
                <component :is="getSortIcon('today_profit')" class="w-3 h-3 text-slate-500" />
              </div>
            </th>
            <th 
              @click="toggleSort('total_profit_rate')"
              class="py-3 px-4 text-right cursor-pointer hover:text-slate-200 transition"
            >
              <div class="flex items-center justify-end space-x-1">
                <span>累计盈亏</span>
                <component :is="getSortIcon('total_profit_rate')" class="w-3 h-3 text-slate-500" />
              </div>
            </th>
            <th class="py-3 px-3 text-center">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-800/50">
          <tr 
            v-for="pos in sortedPositions" 
            :key="pos.id" 
            class="hover:bg-slate-800/40 transition group"
          >
            <!-- 名称与代码 (支持一键复制) -->
            <td class="py-3 px-4">
              <div class="flex items-center space-x-2">
                <div>
                  <div class="font-semibold text-slate-100 flex items-center space-x-1.5">
                    <span>{{ pos.name }}</span>
                    <span 
                      v-if="pos.is_valuation" 
                      class="px-1.5 py-0.2 text-[10px] rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-medium"
                    >
                      估算
                    </span>
                  </div>
                  <div class="text-[11px] text-slate-400 font-mono mt-0.5 flex items-center space-x-1.5">
                    <span 
                      @click="copyCode(pos.code)" 
                      class="hover:text-indigo-400 cursor-pointer underline decoration-dotted underline-offset-2"
                      title="点击复制代码"
                    >
                      {{ pos.code }}
                    </span>
                    <span class="text-slate-600">·</span>
                    <span class="text-slate-500">{{ pos.quote_time || '已同步' }}</span>
                    <span v-if="copiedCode === pos.code" class="text-[10px] text-emerald-400 font-sans font-medium">已复制</span>
                  </div>
                </div>
              </div>
            </td>

            <!-- 平台徽章 (使用独立品牌色，不与盈亏红绿冲突) -->
            <td class="py-3 px-3 text-center">
              <a 
                :href="getPlatformUrl(pos.platform)" 
                target="_blank" 
                rel="noopener noreferrer"
                class="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-medium hover:opacity-80 transition" 
                :class="getPlatformBadgeClass(pos.platform)"
                title="去该平台查看"
              >
                <span>{{ getPlatformName(pos.platform) }}</span>
                <ExternalLink class="w-2.5 h-2.5 opacity-60" />
              </a>
            </td>

            <!-- 最新价 -->
            <td class="py-3 px-3 text-right num-font font-medium text-slate-100">
              ¥{{ pos.current_price?.toFixed(pos.asset_type === 'fund' ? 4 : 2) }}
            </td>

            <!-- 今日涨跌幅 (A股红涨绿跌) -->
            <td class="py-3 px-3 text-right num-font font-bold">
              <span 
                class="inline-block px-1.5 py-0.5 rounded text-[11px]"
                :class="pos.today_profit_rate >= 0 
                  ? 'text-rose-400 bg-rose-500/10' 
                  : 'text-emerald-400 bg-emerald-500/10'"
              >
                {{ pos.today_profit_rate >= 0 ? '+' : '' }}{{ pos.today_profit_rate?.toFixed(2) }}%
              </span>
            </td>

            <!-- 持仓数量 -->
            <td class="py-3 px-3 text-right num-font text-slate-300">
              {{ privacyMode ? '••••••' : pos.shares?.toLocaleString() }}
            </td>

            <!-- 成本单价 -->
            <td class="py-3 px-3 text-right num-font text-slate-400">
              ¥{{ privacyMode ? '••••' : pos.cost_price?.toFixed(pos.asset_type === 'fund' ? 4 : 2) }}
            </td>

            <!-- 市值 -->
            <td class="py-3 px-3 text-right num-font font-bold text-slate-100">
              ¥{{ privacyMode ? '••••••' : formatMoney(pos.market_value) }}
            </td>

            <!-- 今日盈亏 -->
            <td 
              class="py-3 px-3 text-right num-font font-medium"
              :class="pos.today_profit >= 0 ? 'text-rose-400' : 'text-emerald-400'"
            >
              {{ privacyMode ? '••••' : (pos.today_profit >= 0 ? '+' : '') + '¥' + formatMoney(pos.today_profit) }}
            </td>

            <!-- 累计盈亏 -->
            <td class="py-3 px-4 text-right num-font">
              <div class="font-bold" :class="pos.total_profit >= 0 ? 'text-rose-400' : 'text-emerald-400'">
                {{ privacyMode ? '••••' : (pos.total_profit >= 0 ? '+' : '') + '¥' + formatMoney(pos.total_profit) }}
              </div>
              <div class="text-[11px] font-semibold mt-0.5" :class="pos.total_profit >= 0 ? 'text-rose-400/90' : 'text-emerald-400/90'">
                {{ pos.total_profit >= 0 ? '+' : '' }}{{ pos.total_profit_rate?.toFixed(2) }}%
              </div>
            </td>

            <!-- 操作 -->
            <td class="py-3 px-3 text-center">
              <div class="flex items-center justify-center">
                <button 
                  @click="$emit('delete-pos', pos.id)"
                  class="p-1.5 hover:bg-rose-500/10 rounded-lg text-slate-500 hover:text-rose-400 transition"
                  title="删除此持仓"
                >
                  <Trash2 class="w-3.5 h-3.5" />
                </button>
              </div>
            </td>
          </tr>

          <!-- 空状态 -->
          <tr v-if="sortedPositions.length === 0">
            <td colspan="10" class="py-12 text-center text-slate-400 text-xs">
              <div class="max-w-xs mx-auto space-y-2">
                <p>暂无符合条件的持仓</p>
                <p class="text-[11px] text-slate-500">点击右上角【同步持仓】绑定账号，即可自动同步</p>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 表格底部汇总条 -->
    <div 
      v-if="sortedPositions.length > 0"
      class="hidden md:flex items-center justify-between px-4 py-2.5 bg-[#0b101c] border-t border-slate-800 text-xs text-slate-400"
    >
      <div>
        <span>共 </span>
        <span class="font-semibold text-slate-200 num-font">{{ sortedPositions.length }}</span>
        <span> 只</span>
      </div>

      <div class="flex items-center space-x-6 num-font">
        <div>
          <span>市值合计: </span>
          <span class="font-bold text-slate-200">
            ¥{{ privacyMode ? '••••••' : formatMoney(totalFilteredMarketValue) }}
          </span>
        </div>
        <div>
          <span>今日盈亏合计: </span>
          <span 
            class="font-bold"
            :class="totalFilteredTodayProfit >= 0 ? 'text-rose-400' : 'text-emerald-400'"
          >
            {{ privacyMode ? '••••' : (totalFilteredTodayProfit >= 0 ? '+' : '') + '¥' + formatMoney(totalFilteredTodayProfit) }}
          </span>
        </div>
      </div>
    </div>

    <!-- 移动端卡片视图 -->
    <div class="md:hidden divide-y divide-slate-800/80">
      <div v-for="pos in sortedPositions" :key="pos.id" class="p-3.5 space-y-2.5">
        <div class="flex items-start justify-between">
          <div>
            <div class="flex items-center space-x-1.5">
              <span class="font-bold text-sm text-slate-100">{{ pos.name }}</span>
              <a 
                :href="getPlatformUrl(pos.platform)" 
                target="_blank" 
                rel="noopener noreferrer"
                class="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-medium" 
                :class="getPlatformBadgeClass(pos.platform)"
              >
                <span>{{ getPlatformName(pos.platform) }}</span>
              </a>
            </div>
            <div class="text-xs text-slate-400 font-mono mt-0.5 flex items-center space-x-1">
              <span>{{ pos.code }}</span>
              <span class="text-slate-600">·</span>
              <span>{{ pos.quote_time || '已同步' }}</span>
            </div>
          </div>
          <div class="text-right">
            <div class="text-xs font-bold num-font" :class="pos.today_profit_rate >= 0 ? 'text-rose-400' : 'text-emerald-400'">
              {{ pos.today_profit_rate >= 0 ? '+' : '' }}{{ pos.today_profit_rate?.toFixed(2) }}%
            </div>
            <div class="text-[11px] text-slate-400 num-font mt-0.5">
              最新价: ¥{{ pos.current_price?.toFixed(pos.asset_type === 'fund' ? 4 : 2) }}
            </div>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-2 text-xs bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/60 num-font">
          <div>
            <span class="text-slate-400 text-[11px]">市值:</span>
            <div class="font-semibold text-slate-200">
              ¥{{ privacyMode ? '••••••' : formatMoney(pos.market_value) }}
            </div>
          </div>
          <div>
            <span class="text-slate-400 text-[11px]">今日盈亏:</span>
            <div class="font-semibold" :class="pos.today_profit >= 0 ? 'text-rose-400' : 'text-emerald-400'">
              {{ privacyMode ? '••••' : (pos.today_profit >= 0 ? '+' : '') + '¥' + formatMoney(pos.today_profit) }}
            </div>
          </div>
          <div>
            <span class="text-slate-400 text-[11px]">数量/成本:</span>
            <div class="text-slate-300">
              {{ privacyMode ? '••••' : pos.shares }} 份 (¥{{ privacyMode ? '••' : pos.cost_price?.toFixed(2) }})
            </div>
          </div>
          <div>
            <span class="text-slate-400 text-[11px]">累计收益率:</span>
            <div class="font-semibold" :class="pos.total_profit >= 0 ? 'text-rose-400' : 'text-emerald-400'">
              {{ pos.total_profit >= 0 ? '+' : '' }}{{ pos.total_profit_rate?.toFixed(2) }}%
            </div>
          </div>
        </div>

        <div class="flex items-center justify-between text-xs pt-1">
          <span v-if="pos.is_valuation" class="text-[10px] text-amber-400 font-medium">盘中估算</span>
          <span v-else class="text-[10px] text-slate-500">已收盘</span>
          <button @click="$emit('delete-pos', pos.id)" class="text-slate-400 hover:text-rose-400 flex items-center space-x-1">
            <Trash2 class="w-3 h-3" />
            <span>删除</span>
          </button>
        </div>
      </div>

      <div v-if="sortedPositions.length === 0" class="py-8 text-center text-slate-400 text-xs">
        暂无持仓
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Search, Trash2, ExternalLink, X, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-vue-next'

const props = defineProps({
  positions: {
    type: Array,
    default: () => []
  },
  privacyMode: {
    type: Boolean,
    default: false
  }
})

defineEmits(['delete-pos'])

const currentPlatform = ref('all')
const currentType = ref('all')
const searchKeyword = ref('')
const copiedCode = ref('')

// 排序状态
const sortKey = ref('')
const sortOrder = ref('desc') // 'asc' or 'desc'

const toggleSort = (key) => {
  if (sortKey.value === key) {
    if (sortOrder.value === 'desc') {
      sortOrder.value = 'asc'
    } else {
      sortKey.value = ''
      sortOrder.value = 'desc'
    }
  } else {
    sortKey.value = key
    sortOrder.value = 'desc'
  }
}

const getSortIcon = (key) => {
  if (sortKey.value !== key) return ArrowUpDown
  return sortOrder.value === 'asc' ? ArrowUp : ArrowDown
}

const copyCode = (code) => {
  if (!code) return
  navigator.clipboard?.writeText(code)
  copiedCode.value = code
  setTimeout(() => {
    if (copiedCode.value === code) copiedCode.value = ''
  }, 2000)
}

const getPlatformUrl = (p) => {
  const map = {
    eastmoney: 'https://jywg.18.cn/',
    tiantian: 'https://tradeh5.1234567.com.cn/',
    xueqiu: 'https://xueqiu.com/',
    yangjibao: 'https://tradeh5.1234567.com.cn/'
  }
  return map[p] || '#'
}

const getPlatformName = (p) => {
  const map = {
    eastmoney: '东方财富',
    tiantian: '天天基金',
    xueqiu: '雪球基金',
    yangjibao: '养基宝'
  }
  return map[p] || '账户'
}

// 独立的平台颜色，不与红涨绿跌混淆
const getPlatformBadgeClass = (p) => {
  const map = {
    eastmoney: 'bg-sky-500/10 text-sky-400 border border-sky-500/20',
    tiantian: 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
    xueqiu: 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20',
    yangjibao: 'bg-teal-500/10 text-teal-400 border border-teal-500/20'
  }
  return map[p] || 'bg-slate-800 text-slate-300 border border-slate-700'
}

const formatMoney = (val) => {
  if (val === undefined || val === null) return '0.00'
  return Number(val).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// 平台 Tab 动态统计数量
const platformTabsWithCount = computed(() => {
  const allCount = props.positions.length
  const emCount = props.positions.filter(p => p.platform === 'eastmoney').length
  const ttCount = props.positions.filter(p => p.platform === 'tiantian').length
  const xqCount = props.positions.filter(p => p.platform === 'xueqiu').length
  const yjbCount = props.positions.filter(p => p.platform === 'yangjibao').length

  const tabs = [
    { label: '全部平台', value: 'all', count: allCount },
    { label: '东方财富 A股', value: 'eastmoney', count: emCount },
    { label: '天天基金', value: 'tiantian', count: ttCount },
    { label: '雪球基金', value: 'xueqiu', count: xqCount },
  ]
  if (yjbCount > 0) {
    tabs.push({ label: '养基宝', value: 'yangjibao', count: yjbCount })
  }
  return tabs
})

const filteredPositions = computed(() => {
  return props.positions.filter(p => {
    if (currentPlatform.value !== 'all' && p.platform !== currentPlatform.value) {
      return false
    }
    if (currentType.value !== 'all' && p.asset_type !== currentType.value) {
      return false
    }
    if (searchKeyword.value) {
      const kw = searchKeyword.value.toLowerCase().trim()
      const matchCode = p.code.toLowerCase().includes(kw)
      const matchName = p.name ? p.name.toLowerCase().includes(kw) : false
      if (!matchCode && !matchName) return false
    }
    return true
  })
})

const sortedPositions = computed(() => {
  const list = [...filteredPositions.value]
  if (!sortKey.value) return list
  return list.sort((a, b) => {
    const valA = Number(a[sortKey.value]) || 0
    const valB = Number(b[sortKey.value]) || 0
    return sortOrder.value === 'asc' ? valA - valB : valB - valA
  })
})

const totalFilteredMarketValue = computed(() => {
  return sortedPositions.value.reduce((sum, p) => sum + (Number(p.market_value) || 0), 0)
})

const totalFilteredTodayProfit = computed(() => {
  return sortedPositions.value.reduce((sum, p) => sum + (Number(p.today_profit) || 0), 0)
})
</script>
