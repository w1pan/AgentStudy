import type { KcalRange } from '@/api/qingheng'

export function touchesTarget(value: KcalRange, target: KcalRange): boolean {
  return value.low <= target.high && value.high >= target.low
}

export function currentRecordDate(): string {
  return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai' }).format(new Date())
}
