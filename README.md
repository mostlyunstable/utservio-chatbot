# Utservio AI Chatbot

A premium, glassmorphic React widget built to support the Utservio customer experience. 

Utservio is a micro-home cleaning & subscription service in Chennai. This standalone frontend provides an intelligent chatbot interface to help customers understand pricing, service coverage, and subscription plans.

## Features

- **Premium Aesthetics**: Stunning glassmorphic design, dynamic background orbs, and holographic ticket cards, tuned to Utservio's exact brand colors (Dark & Gold).
- **Interactive Knowledge Base**: Built-in logic to handle FAQs seamlessly:
  - Sweep & Mop, Fan Cleaning, Bathroom Cleaning pricing.
  - Active coverage hubs (OMR, ECR, Perungudi, etc.).
  - Recurrent monthly subscriptions.
- **Micro-animations**: Staggered quick replies, realistic typing indicators, and smooth chat sliding animations.
- **Lucide Icons**: Crisp, scalable vector iconography for a polished look.

## Tech Stack

- **React 18**
- **Vite**
- **Vanilla CSS** (for precise, high-performance styling)
- **Lucide React** (icons)

## Quick Start

1. Install dependencies:
   ```bash
   npm install
   ```

2. Run the development server:
   ```bash
   npm run dev
   ```

3. Build for production:
   ```bash
   npm run build
   ```

## Future Roadmap

- Integrate with the `mostlyunstable/forge` backend (via NVIDIA NIM and Qdrant) to turn the hardcoded FAQ logic into a fully dynamic AI-driven LLM application.
