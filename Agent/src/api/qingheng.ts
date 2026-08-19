import { client } from './client'

export type MealType = 'breakfast' | 'lunch' | 'dinner' | 'custom'
export type DeficitPreset = 'gentle' | 'standard'
export type BiologicalSex = 'male' | 'female'
export type Intensity = 'low' | 'medium' | 'high'
export type AdviceCardType = 'status' | 'next_meal' | 'risk_or_encouragement'
export type EstimateConfidence = 'high' | 'medium' | 'low'
export type PortionBasis = 'count' | 'container' | 'package' | 'geometry' | 'mixed' | 'visual'

export interface KcalRange {
  low: number
  high: number
}

export interface ProfilePayload {
  age: number
  biological_sex: BiologicalSex
  height_cm: number
  current_weight_kg: number
  deficit_preset: DeficitPreset
}

export interface Profile extends ProfilePayload {
  bmi: number
  rmr_kcal: number
  target_deficit: KcalRange
  updated_at: string
}

export interface FoodTemplate {
  id: string
  name: string
  aliases: string[]
  category: string
  kcal_estimate: number
  uncertainty_pct: number
  kcal_per_100g: KcalRange
  units: Record<string, number>
  source_name: string
  source_version: string
  source_url: string | null
}

export interface MetActivity {
  id: string
  name: string
  mets: Record<Intensity, number>
  source_version: string
}

export interface ManualMealItemPayload {
  template_id?: string
  name?: string
  quantity: number
  unit: string
  kcal?: KcalRange
}

export interface ManualMealPayload {
  meal_type: MealType
  custom_meal_name: string | null
  recorded_time: string
  items: ManualMealItemPayload[]
}

export interface MealItem {
  id: string
  template_id: string | null
  name: string
  category: string
  quantity: number
  unit: string
  grams: KcalRange | null
  kcal: KcalRange
  estimate_source: 'template' | 'user' | 'ai'
  estimate_confidence: EstimateConfidence | null
  portion_basis: PortionBasis | null
  portion_detail: string | null
  portion_confidence: EstimateConfidence | null
  density_confidence: EstimateConfidence | null
  source_name: string
  source_version: string
}

export interface Meal {
  id: string
  meal_type: MealType
  custom_meal_name: string | null
  display_name: string
  entry_method: 'manual' | 'photo'
  recorded_date: string
  recorded_time: string
  kcal: KcalRange
  estimate_confidence: EstimateConfidence | null
  editable: boolean
  deletable: boolean
  items: MealItem[]
}

export interface ExercisePayload {
  activity_id: string
  intensity: Intensity
  duration_minutes: number
  recorded_time: string
  manual_kcal: KcalRange | null
}

export interface Exercise {
  id: string
  activity_id: string
  activity_name: string
  intensity: Intensity
  duration_minutes: number
  recorded_date: string
  recorded_time: string
  kcal: KcalRange
  estimate_source: 'met' | 'manual_adjusted'
  editable: boolean
  deletable: boolean
}

export interface Weight {
  recorded_date: string
  weight_kg: number
  editable: boolean
}

export interface DailySummary {
  record_date: string
  data_version: number
  rmr_kcal: number
  intake: KcalRange
  baseline_expenditure: KcalRange
  exercise_expenditure: KcalRange
  total_expenditure: KcalRange
  deficit: KcalRange
  target_deficit: KcalRange
  risk_flags: Array<'underweight_bmi' | 'target_below_rmr'>
}

export interface DayDetail {
  summary: DailySummary
  meals: Meal[]
  exercises: Exercise[]
  weight: Weight | null
}

export interface AdviceCard {
  type: AdviceCardType
  title: string
  body: string
  bullets: string[]
}

export interface AdviceResponse {
  record_date: string
  data_version: number
  cards: AdviceCard[]
}

export interface FollowUpMessage {
  role: 'user' | 'assistant'
  content: string
}

export const api = {
  async getProfile() {
    return (await client.get<Profile>('/profile')).data
  },
  async saveProfile(payload: ProfilePayload) {
    return (await client.put<Profile>('/profile', payload)).data
  },
  async getToday() {
    return (await client.get<DayDetail>('/today')).data
  },
  async getHistoryMonth(month: string) {
    return (await client.get<{ month: string; dates: string[] }>('/history', { params: { month } })).data
  },
  async getHistoryDay(recordDate: string) {
    return (await client.get<DayDetail>(`/history/${recordDate}`)).data
  },
  async searchFoodTemplates(query: string) {
    return (await client.get<FoodTemplate[]>('/food-templates', { params: { query } })).data
  },
  async getMetActivities() {
    return (await client.get<MetActivity[]>('/met-activities')).data
  },
  async createManualMeal(payload: ManualMealPayload) {
    return (await client.post<Meal>('/meals/manual', payload)).data
  },
  async updateManualMeal(id: string, payload: ManualMealPayload) {
    return (await client.patch<Meal>(`/meals/${id}`, payload)).data
  },
  async createPhotoMeal(file: File, mealType: MealType, customMealName: string | null) {
    return (
      await client.post<Meal>('/meals/photo', file, {
        params: { meal_type: mealType, custom_meal_name: customMealName || undefined },
        headers: { 'Content-Type': 'application/octet-stream' },
        timeout: 120_000,
      })
    ).data
  },
  async deleteMeal(id: string) {
    await client.delete(`/meals/${id}`)
  },
  async upsertWeight(weightKg: number) {
    return (await client.put<Weight>('/weights/today', { weight_kg: weightKg })).data
  },
  async createExercise(payload: ExercisePayload) {
    return (await client.post<Exercise>('/exercises', payload)).data
  },
  async updateExercise(id: string, payload: ExercisePayload) {
    return (await client.patch<Exercise>(`/exercises/${id}`, payload)).data
  },
  async deleteExercise(id: string) {
    await client.delete(`/exercises/${id}`)
  },
  async generateAdvice() {
    return (
      await client.post<AdviceResponse>('/advice', undefined, {
        timeout: 120_000,
      })
    ).data
  },
  async clearHistory() {
    await client.post('/history/clear', { confirmation: '清空全部历史记录' })
  },
}

export async function streamAdviceFollowUp(
  cardType: AdviceCardType,
  message: string,
  history: FollowUpMessage[],
  onText: (text: string) => void,
) {
  const response = await fetch('/api/v1/advice/follow-up', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ card_type: cardType, message, history }),
  })
  if (!response.ok || !response.body) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(payload.detail || '追问暂时不可用')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() || ''
    for (const event of events) {
      if (event.startsWith('event: error')) throw new Error('追问暂时不可用，请稍后重试')
      const dataLine = event.split('\n').find((line) => line.startsWith('data: '))
      if (!dataLine || event.startsWith('event: done')) continue
      const payload = JSON.parse(dataLine.slice(6))
      if (payload.text) onText(payload.text)
    }
  }
}
