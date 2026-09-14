import { Activity, ArrowRight, Check, Dumbbell, LockKeyhole, Play, Zap } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { WorkoutInfoModal } from '../components/common/WorkoutInfoModal'
import { PageHeader } from '../components/layout/PageHeader'
import { requestDesktopClientLaunch } from '../lib/desktopClient'

type ExerciseId = 'squat' | 'burpee' | 'pushup'

const exercises: Array<{
  id: ExerciseId
  name: string
  englishName: string
  description: string
  available: boolean
  icon: typeof Dumbbell
}> = [
  {
    id: 'squat',
    name: '스쿼트',
    englishName: 'Squat',
    description: '하체 근력과 자세 균형을 위한 기본 운동',
    available: true,
    icon: Dumbbell,
  },
  {
    id: 'burpee',
    name: '버피',
    englishName: 'Burpee',
    description: '전신 근력과 심폐 지구력을 위한 복합 운동',
    available: false,
    icon: Zap,
  },
  {
    id: 'pushup',
    name: '팔굽혀펴기',
    englishName: 'Push-up',
    description: '상체 근력과 코어 안정성을 위한 기본 운동',
    available: false,
    icon: Activity,
  },
]

export function ExerciseHomePage() {
  const [selectedExercise, setSelectedExercise] = useState<ExerciseId | null>(null)
  const [showStartGuide, setShowStartGuide] = useState(false)
  const [launching, setLaunching] = useState(false)
  const launchCleanup = useRef<() => void>(() => undefined)
  const selected = exercises.find(({ id }) => id === selectedExercise)

  useEffect(() => () => launchCleanup.current(), [])

  const startWorkout = () => {
    if (selectedExercise !== 'squat') return
    launchCleanup.current()
    setLaunching(true)
    setShowStartGuide(false)
    launchCleanup.current = requestDesktopClientLaunch(
      'squat',
      () => { setLaunching(false); setShowStartGuide(true) },
      () => setLaunching(false),
    )
  }

  return (
    <div className="exercise-home-page">
      <PageHeader title="운동 선택" subtitle="오늘 집중할 운동을 선택하고 AI 코칭을 준비하세요." />

      <section className="exercise-intro">
        <div>
          <p className="eyebrow">AI CAMERA WORKOUT</p>
          <h2>나에게 맞는 운동 루트를 시작하세요.</h2>
          <p>현재 스쿼트 자세 분석과 반복 횟수 기록을 이용할 수 있습니다.</p>
        </div>
        <span className="exercise-live-pill"><i /> AI 준비 완료</span>
      </section>

      <section className="exercise-card-grid" aria-label="운동 목록">
        {exercises.map(({ id, name, englishName, description, available, icon: Icon }) => {
          const isSelected = selectedExercise === id
          return (
            <article key={id} className={`exercise-card ${isSelected ? 'exercise-card-selected' : ''} ${available ? '' : 'exercise-card-disabled'}`}>
              <div className="flex items-start justify-between gap-3">
                <span className="exercise-card-icon"><Icon size={24} /></span>
                <span className={available ? 'exercise-available' : 'exercise-coming'}>
                  {available ? <><Check size={13} /> 사용 가능</> : <><LockKeyhole size={12} /> 서비스 준비 중</>}
                </span>
              </div>
              <p className="mt-8 text-[11px] font-extrabold uppercase tracking-[.18em] text-lime/60">{englishName}</p>
              <h3>{name}</h3>
              <p className="exercise-card-description">{description}</p>
              <button
                type="button"
                className={available ? 'exercise-select-button' : 'exercise-disabled-button'}
                disabled={!available}
                aria-pressed={available ? isSelected : undefined}
                onClick={() => available && setSelectedExercise(id)}
              >
                {available ? (isSelected ? '선택됨' : '선택하기') : 'Coming Soon'}
                {available && <ArrowRight size={16} />}
              </button>
            </article>
          )
        })}
      </section>

      <section className={`exercise-selection ${selected ? 'exercise-selection-active' : ''}`} aria-live="polite">
        <div>
          <p className="text-[10px] font-extrabold tracking-[.18em] text-lime/60">선택 운동</p>
          <h3>{selected ? selected.englishName.toUpperCase() : '운동을 선택해 주세요'}</h3>
          <p>{selected ? '올바른 스쿼트 자세를 인식하고 반복 횟수를 기록합니다.' : '사용 가능한 운동 카드를 선택하면 시작할 수 있습니다.'}</p>
        </div>
        <button className="btn-primary justify-center px-6 py-3.5" disabled={!selected || launching} onClick={startWorkout}>
          <Play size={17} fill="currentColor" /> {launching ? 'AI Client 연결 중…' : '운동 시작'}
        </button>
      </section>

      {showStartGuide && <WorkoutInfoModal exercise="squat" retry={startWorkout} close={() => setShowStartGuide(false)} />}
    </div>
  )
}
