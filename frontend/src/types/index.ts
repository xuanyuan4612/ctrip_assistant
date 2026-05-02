export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  bookingCards?: BookingCard[]
  timestamp: string
  streaming?: boolean
}

export interface BookingCard {
  type: 'flight' | 'hotel' | 'car_rental' | 'excursion'
  data: Record<string, unknown>
}

export interface Session {
  id: string
  title: string
  lastMessage: string
  updatedAt: string
  messageCount: number
}

export interface User {
  id: number
  username: string
  phone?: string
  realName?: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  id: number
  username: string
  token: string
  phone?: string
  realName?: string
}

export interface ChatResponse {
  assistant: string
  thread_id: string
}

export interface AdminStats {
  totalUsers: number
  totalConversations: number
  totalTokens: number
  totalCost: number
  activeToday: number
}
