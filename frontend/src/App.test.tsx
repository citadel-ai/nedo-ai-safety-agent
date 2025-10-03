import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from './App'

describe('App', () => {
  it('renders the Japan Helpdesk interface', () => {
    render(<App />)
    
    // Check if the welcome message is rendered
    expect(screen.getByText(/こんにちは！日本での行政手続きについてお手伝いします/)).toBeDefined()
    expect(screen.getByText(/Hello! I'm here to help you with administrative procedures in Japan/)).toBeDefined()
  })
})
