/**
 * UI Component Library
 * 
 * A comprehensive, reusable UI component library built with Tailwind CSS, 
 * TypeScript, and React. All components follow the existing design patterns 
 * in the codebase.
 * 
 * Usage:
 * import { Button, Input, Modal } from '@/components/ui'
 */

// Simple Components
export { Badge, type BadgeProps } from './Badge'
export { LoadingSpinner, type LoadingSpinnerProps } from './LoadingSpinner'
export {
  Card,
  CardHeader,
  CardBody,
  CardFooter,
  CardTitle,
  CardDescription,
  type CardProps,
  type CardHeaderProps,
  type CardBodyProps,
  type CardFooterProps,
  type CardTitleProps,
  type CardDescriptionProps,
} from './Card'

// Form Components
export { Input, type InputProps } from './Input'
export { Select, type SelectProps, type SelectOption } from './Select'
export { Toggle, type ToggleProps } from './Toggle'
export { Slider, type SliderProps } from './Slider'
export { FormField, type FormFieldProps } from './FormField'

// Interactive Components
export { Button, type ButtonProps } from './Button'
export {
  SearchInput,
  type SearchInputProps,
  type SearchSuggestion,
} from './SearchInput'

// Complex Components
export {
  Tabs,
  TabPanel,
  TabsWithContent,
  type TabsProps,
  type Tab,
  type TabPanelProps,
  type TabsWithContentProps,
} from './Tabs'
export { Modal, ModalFooter, type ModalProps, type ModalFooterProps } from './Modal'
export { Tooltip, type TooltipProps } from './Tooltip'
