<template>
  <header class="border-b border-slate-800/80 bg-[#0c121d]/90 backdrop-blur-md sticky top-0 z-30 transition-all">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <!-- Logo & 品牌状态 -->
      <div class="flex items-center space-x-3.5">
        <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500/20 via-slate-800 to-indigo-900/40 border border-indigo-500/30 flex items-center justify-center shadow-inner group">
          <TrendingUp class="w-5 h-5 text-indigo-400 group-hover:scale-110 transition-transform" />
        </div>
        <div>
          <div class="flex items-center space-x-2.5">
            <span class="font-bold text-base sm:text-lg tracking-tight text-white flex items-center space-x-1">
              <span>PortfolioHub</span>
              <span class="text-xs px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-medium ml-1">资产看板</span>
            </span>
            <div class="hidden sm:inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[11px] font-medium">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>实时行情</span>
            </div>
          </div>
          <p class="text-[11px] text-slate-400 hidden md:flex items-center space-x-1.5 mt-0.5">
            <span>东方财富</span>
            <span class="text-slate-600">·</span>
            <span>天天基金</span>
            <span class="text-slate-600">·</span>
            <span>雪球</span>
            <span class="text-slate-600">·</span>
            <span>养基宝</span>
            <span class="text-slate-600">·</span>
            <span class="text-slate-500">自动同步持仓</span>
          </p>
        </div>
      </div>

      <!-- 右侧综合操作区 -->
      <div class="flex items-center space-x-2 sm:space-x-2.5">
        <!-- 隐私模式切换 (隐藏/显示敏感资金) -->
        <button 
          @click="$emit('toggle-privacy')"
          class="p-2 sm:px-2.5 sm:py-1.5 text-xs font-medium rounded-lg border transition flex items-center space-x-1.5"
          :class="privacyMode 
            ? 'bg-amber-500/10 border-amber-500/30 text-amber-300 hover:bg-amber-500/20' 
            : 'bg-slate-800/80 border-slate-700/70 text-slate-300 hover:bg-slate-700 hover:text-white'"
          :title="privacyMode ? '点击显示金额' : '点击隐藏金额'"
        >
          <component :is="privacyMode ? EyeOff : Eye" class="w-3.5 h-3.5" />
          <span class="hidden lg:inline">{{ privacyMode ? '金额已隐藏' : '隐藏金额' }}</span>
        </button>

        <!-- 刷新行情 -->
        <button 
          @click="$emit('refresh')"
          :disabled="refreshing"
          class="flex items-center space-x-1.5 px-2.5 sm:px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 border border-slate-700/70 transition active:scale-95 disabled:opacity-50"
          :title="lastUpdated ? `最近更新: ${lastUpdated}` : '刷新最新价格'"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="{'animate-spin text-indigo-400': refreshing}" />
          <span class="hidden sm:inline">{{ refreshing ? '刷新中...' : '刷新价格' }}</span>
        </button>

        <!-- 账户同步 (主操作 CTA) -->
        <button 
          @click="$emit('open-accounts')"
          class="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white border border-indigo-500/40 shadow-sm shadow-indigo-600/20 transition active:scale-95"
          title="绑定账号或一键同步持仓"
        >
          <Layers class="w-3.5 h-3.5" />
          <span>同步持仓</span>
        </button>

        <!-- AI 分析 -->
        <button 
          @click="$emit('open-ai')"
          class="flex items-center space-x-1.5 px-2.5 sm:px-3 py-1.5 text-xs font-medium rounded-lg bg-purple-950/60 hover:bg-purple-900/80 text-purple-200 border border-purple-700/50 shadow-sm transition active:scale-95"
          title="AI 智能分析持仓与诊断"
        >
          <Sparkles class="w-3.5 h-3.5 text-purple-400" />
          <span class="hidden sm:inline">AI 分析</span>
        </button>

        <!-- 市场风向 -->
        <button 
          @click="$emit('open-kol')"
          class="flex items-center space-x-1.5 px-2.5 sm:px-3 py-1.5 text-xs font-medium rounded-lg bg-amber-950/60 hover:bg-amber-900/80 text-amber-200 border border-amber-700/50 shadow-sm transition active:scale-95"
          title="全自动市场风向与板块动态，客观防追高"
        >
          <Compass class="w-3.5 h-3.5 text-amber-400" />
          <span class="hidden sm:inline">市场风向</span>
        </button>

        <!-- 涨跌提醒 -->
        <button 
          @click="$emit('open-alerts')"
          class="flex items-center space-x-1 px-2 sm:px-2.5 py-1.5 text-xs font-medium rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 hover:text-white border border-slate-700/70 transition"
          title="设置涨跌与止盈止损提醒"
        >
          <Bell class="w-3.5 h-3.5 text-amber-400" />
          <span class="hidden md:inline">提醒</span>
        </button>

        <!-- 通知设置 -->
        <button 
          @click="$emit('open-notify')"
          class="flex items-center space-x-1 px-2 sm:px-2.5 py-1.5 text-xs font-medium rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 hover:text-white border border-slate-700/70 transition"
          title="微信推送提醒设置"
        >
          <Send class="w-3.5 h-3.5 text-emerald-400" />
          <span class="hidden md:inline">通知</span>
        </button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { TrendingUp, RefreshCw, Layers, Bell, Send, Sparkles, Compass, Eye, EyeOff } from 'lucide-vue-next'

defineProps({
  refreshing: Boolean,
  privacyMode: Boolean,
  lastUpdated: String
})
defineEmits(['refresh', 'open-accounts', 'open-alerts', 'open-notify', 'open-ai', 'open-kol', 'toggle-privacy'])
</script>


