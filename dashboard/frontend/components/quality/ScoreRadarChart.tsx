'use client'

import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend } from 'recharts'
import { Card, CardHeader, CardBody, CardTitle } from '@/components/ui'
import type { ScoreComponents } from '@/types/quality'
import { cn } from '@/lib/utils'

export interface ScoreRadarChartProps {
  currentScore: ScoreComponents
  previousScore?: ScoreComponents | null
  targets?: ScoreComponents
  className?: string
  title?: string
}

const componentLabels: Record<keyof ScoreComponents, string> = {
  completeness: 'Completeness',
  validity: 'Validity',
  consistency: 'Consistency',
  freshness: 'Freshness',
  uniqueness: 'Uniqueness',
  accuracy: 'Accuracy',
}

const componentOrder: (keyof ScoreComponents)[] = [
  'completeness',
  'validity',
  'consistency',
  'freshness',
  'uniqueness',
  'accuracy',
]

export default function ScoreRadarChart({
  currentScore,
  previousScore,
  targets,
  className,
  title = 'Component Breakdown',
}: ScoreRadarChartProps) {
  // Prepare data for radar chart
  const chartData = componentOrder.map((key) => {
    const dataPoint: {
      component: string
      current: number
      previous?: number
      target?: number
    } = {
      component: componentLabels[key],
      current: currentScore[key],
    }
    if (previousScore) {
      dataPoint.previous = previousScore[key]
    }
    if (targets) {
      dataPoint.target = targets[key]
    }
    return dataPoint
  })

  return (
    <Card variant="glass" className={cn('bg-surface-900/30', className)}>
      <CardHeader>
        <CardTitle className="text-lg font-semibold text-white">{title}</CardTitle>
      </CardHeader>
      <CardBody>
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={chartData}>
              <PolarGrid stroke="rgba(148, 163, 184, 0.2)" />
              <PolarAngleAxis
                dataKey="component"
                tick={{ fill: 'rgb(148, 163, 184)', fontSize: 12 }}
                className="text-slate-400"
              />
              <PolarRadiusAxis
                angle={90}
                domain={[0, 100]}
                tick={{ fill: 'rgb(148, 163, 184)', fontSize: 10 }}
              />
              <Radar
                name="Current"
                dataKey="current"
                stroke="rgb(34, 211, 238)"
                fill="rgba(34, 211, 238, 0.3)"
                fillOpacity={0.6}
              />
              {previousScore && (
                <Radar
                  name="Previous"
                  dataKey="previous"
                  stroke="rgb(148, 163, 184)"
                  fill="rgba(148, 163, 184, 0.2)"
                  fillOpacity={0.4}
                />
              )}
              {targets && (
                <Radar
                  name="Target"
                  dataKey="target"
                  stroke="rgb(16, 185, 129)"
                  fill="none"
                  strokeDasharray="5 5"
                />
              )}
              <Legend
                wrapperStyle={{ color: 'rgb(148, 163, 184)', fontSize: '12px' }}
                iconType="line"
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </CardBody>
    </Card>
  )
}
