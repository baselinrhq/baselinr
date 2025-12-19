'use client'

import {
  Badge,
  Button,
  Card,
  CardHeader,
  CardBody,
  CardFooter,
  CardTitle,
  CardDescription,
  Input,
  Select,
  Toggle,
  Slider,
  Modal,
  ModalFooter,
  Tooltip,
  Tabs,
  SearchInput,
  LoadingSpinner,
  FormField,
} from '@/components/ui'
import { useState } from 'react'
import { CheckCircle } from 'lucide-react'

export default function UITestPage() {
  const [modalOpen, setModalOpen] = useState(false)
  const [toggleValue, setToggleValue] = useState(false)
  const [sliderValue, setSliderValue] = useState(50)
  const [searchValue, setSearchValue] = useState('')
  const [activeTab, setActiveTab] = useState('tab1')
  const [selectValue, setSelectValue] = useState<string>('')

  const searchSuggestions = [
    { value: 'result1', label: 'Search Result 1' },
    { value: 'result2', label: 'Search Result 2' },
    { value: 'result3', label: 'Search Result 3' },
  ]

  return (
    <div className="container mx-auto p-8 space-y-8 max-w-6xl">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">UI Component Library Test Page</h1>
        <p className="text-gray-600">Test all components from the shared UI component library</p>
      </div>

      {/* Buttons */}
      <Card>
        <CardHeader>
          <CardTitle>Buttons</CardTitle>
          <CardDescription>Various button styles and states</CardDescription>
        </CardHeader>
        <CardBody className="flex gap-4 flex-wrap">
          <Button>Default</Button>
          <Button variant="primary">Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="destructive">Destructive</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button disabled>Disabled</Button>
          <Button loading>Loading</Button>
          <Button size="sm">Small</Button>
          <Button size="lg">Large</Button>
        </CardBody>
      </Card>

      {/* Badges */}
      <Card>
        <CardHeader>
          <CardTitle>Badges</CardTitle>
          <CardDescription>Status indicators and labels</CardDescription>
        </CardHeader>
        <CardBody className="flex gap-4 flex-wrap items-center">
          <Badge>Default</Badge>
          <Badge variant="success">Success</Badge>
          <Badge variant="warning">Warning</Badge>
          <Badge variant="error">Error</Badge>
          <Badge variant="info">Info</Badge>
          <Badge variant="success" outline>Success Outline</Badge>
          <Badge variant="error" outline>Error Outline</Badge>
          <Badge size="sm">Small</Badge>
          <Badge variant="success" icon={<CheckCircle className="w-3 h-3" />}>
            With Icon
          </Badge>
        </CardBody>
      </Card>

      {/* Inputs */}
      <Card>
        <CardHeader>
          <CardTitle>Inputs</CardTitle>
          <CardDescription>Text input fields</CardDescription>
        </CardHeader>
        <CardBody className="space-y-4">
          <Input placeholder="Enter text..." />
          <Input type="password" placeholder="Password" />
          <Input disabled placeholder="Disabled input" />
          <Input type="email" placeholder="Email address" />
          <Input type="number" placeholder="Number input" />
        </CardBody>
      </Card>

      {/* FormField */}
      <Card>
        <CardHeader>
          <CardTitle>Form Field</CardTitle>
          <CardDescription>Input with label and error handling</CardDescription>
        </CardHeader>
        <CardBody className="space-y-4">
          <FormField label="Email Address" required>
            <Input type="email" placeholder="Enter email" />
          </FormField>
          <FormField label="Password" required error="This field is required">
            <Input type="password" placeholder="Enter password" />
          </FormField>
          <FormField label="Optional Field" helperText="This is optional">
            <Input placeholder="Optional input" />
          </FormField>
        </CardBody>
      </Card>

      {/* Select */}
      <Card>
        <CardHeader>
          <CardTitle>Select</CardTitle>
          <CardDescription>Dropdown selection component</CardDescription>
        </CardHeader>
        <CardBody>
          <Select
            value={selectValue}
            onChange={setSelectValue}
            options={[
              { value: '1', label: 'Option 1' },
              { value: '2', label: 'Option 2' },
              { value: '3', label: 'Option 3' },
              { value: '4', label: 'Option 4' },
            ]}
            placeholder="Choose an option"
          />
          {selectValue && (
            <p className="mt-2 text-sm text-gray-600">Selected: {selectValue}</p>
          )}
        </CardBody>
      </Card>

      {/* Toggle */}
      <Card>
        <CardHeader>
          <CardTitle>Toggle</CardTitle>
          <CardDescription>Switch/toggle component</CardDescription>
        </CardHeader>
        <CardBody className="space-y-4">
          <Toggle
            checked={toggleValue}
            onChange={setToggleValue}
            label="Enable notifications"
          />
          <Toggle
            checked={!toggleValue}
            onChange={(val) => setToggleValue(!val)}
            label="Dark mode"
            labelPosition="left"
          />
          <Toggle
            checked={toggleValue}
            onChange={setToggleValue}
            label="Small toggle"
            size="sm"
          />
          <Toggle
            checked={toggleValue}
            onChange={setToggleValue}
            label="Large toggle"
            size="lg"
          />
          <Toggle
            checked={false}
            onChange={() => {}}
            label="Disabled toggle"
            disabled
          />
          <p className="text-sm text-gray-600 mt-2">Toggle value: {toggleValue ? 'ON' : 'OFF'}</p>
        </CardBody>
      </Card>

      {/* Slider */}
      <Card>
        <CardHeader>
          <CardTitle>Slider</CardTitle>
          <CardDescription>Range slider component</CardDescription>
        </CardHeader>
        <CardBody>
          <Slider
            value={sliderValue}
            onChange={(val) => setSliderValue(typeof val === 'number' ? val : val[0])}
            min={0}
            max={100}
            step={1}
            label="Volume"
            showValue
          />
          <p className="mt-2 text-sm text-gray-600">Value: {sliderValue}</p>
          <div className="mt-4">
            <Slider
              value={30}
              onChange={() => {}}
              min={0}
              max={100}
              label="Disabled slider"
              disabled
            />
          </div>
        </CardBody>
      </Card>

      {/* Modal */}
      <Card>
        <CardHeader>
          <CardTitle>Modal</CardTitle>
          <CardDescription>Dialog/modal component</CardDescription>
        </CardHeader>
        <CardBody className="space-y-4">
          <div className="flex gap-4 flex-wrap">
            <Button onClick={() => setModalOpen(true)}>Open Small Modal</Button>
            <Button variant="secondary" onClick={() => setModalOpen(true)}>
              Open Large Modal
            </Button>
          </div>
          <Modal
            isOpen={modalOpen}
            onClose={() => setModalOpen(false)}
            title="Test Modal"
            size="md"
          >
            <div className="space-y-4">
              <p>This is a test modal. You can close it by:</p>
              <ul className="list-disc list-inside space-y-1 text-gray-600">
                <li>Clicking the X button</li>
                <li>Clicking outside the modal (backdrop)</li>
                <li>Pressing the Escape key</li>
              </ul>
            </div>
            <ModalFooter>
              <Button variant="secondary" onClick={() => setModalOpen(false)}>
                Cancel
              </Button>
              <Button onClick={() => setModalOpen(false)}>Confirm</Button>
            </ModalFooter>
          </Modal>
        </CardBody>
      </Card>

      {/* Tooltip */}
      <Card>
        <CardHeader>
          <CardTitle>Tooltip</CardTitle>
          <CardDescription>Hover tooltip component</CardDescription>
        </CardHeader>
        <CardBody className="flex gap-4 flex-wrap">
          <Tooltip content="This is a tooltip on the top!">
            <Button>Hover me (top)</Button>
          </Tooltip>
          <Tooltip content="Tooltip on the right" position="right">
            <Button variant="secondary">Hover me (right)</Button>
          </Tooltip>
          <Tooltip content="Tooltip on the bottom" position="bottom">
            <Button variant="outline">Hover me (bottom)</Button>
          </Tooltip>
          <Tooltip content="Tooltip on the left" position="left">
            <Button variant="ghost">Hover me (left)</Button>
          </Tooltip>
        </CardBody>
      </Card>

      {/* Tabs */}
      <Card>
        <CardHeader>
          <CardTitle>Tabs</CardTitle>
          <CardDescription>Tab navigation component</CardDescription>
        </CardHeader>
        <CardBody>
          <Tabs
            tabs={[
              { id: 'tab1', label: 'Tab 1' },
              { id: 'tab2', label: 'Tab 2' },
              { id: 'tab3', label: 'Tab 3' },
              { id: 'tab4', label: 'Disabled Tab', disabled: true },
            ]}
            activeTab={activeTab}
            onChange={setActiveTab}
          />
          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
            {activeTab === 'tab1' && <p>Content for Tab 1</p>}
            {activeTab === 'tab2' && <p>Content for Tab 2</p>}
            {activeTab === 'tab3' && <p>Content for Tab 3</p>}
          </div>
        </CardBody>
      </Card>

      {/* SearchInput */}
      <Card>
        <CardHeader>
          <CardTitle>Search Input</CardTitle>
          <CardDescription>Search input with suggestions</CardDescription>
        </CardHeader>
        <CardBody>
          <SearchInput
            value={searchValue}
            onChange={setSearchValue}
            placeholder="Search..."
            suggestions={searchSuggestions}
            onSearch={(value) => console.log('Search:', value)}
          />
          {searchValue && (
            <p className="mt-2 text-sm text-gray-600">Current search: {searchValue}</p>
          )}
        </CardBody>
      </Card>

      {/* Loading Spinner */}
      <Card>
        <CardHeader>
          <CardTitle>Loading Spinner</CardTitle>
          <CardDescription>Loading indicators</CardDescription>
        </CardHeader>
        <CardBody>
          <div className="flex gap-8 items-center">
            <div className="text-center">
              <LoadingSpinner size="sm" />
              <p className="mt-2 text-xs text-gray-600">Small</p>
            </div>
            <div className="text-center">
              <LoadingSpinner size="md" />
              <p className="mt-2 text-xs text-gray-600">Medium</p>
            </div>
            <div className="text-center">
              <LoadingSpinner size="lg" />
              <p className="mt-2 text-xs text-gray-600">Large</p>
            </div>
            <div className="text-center">
              <LoadingSpinner size="md" />
              <p className="mt-2 text-xs text-gray-600">Dots</p>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Card Variations */}
      <Card>
        <CardHeader>
          <CardTitle>Card Component</CardTitle>
          <CardDescription>This card demonstrates the Card component structure</CardDescription>
        </CardHeader>
        <CardBody>
          <p>This is the card body content. Cards can have headers, bodies, and footers.</p>
        </CardBody>
        <CardFooter>
          <Button size="sm">Action Button</Button>
        </CardFooter>
      </Card>

      {/* Combined Example */}
      <Card>
        <CardHeader>
          <CardTitle>Combined Example</CardTitle>
          <CardDescription>Components working together</CardDescription>
        </CardHeader>
        <CardBody className="space-y-4">
          <FormField label="User Settings" required>
            <div className="space-y-3">
              <Toggle
                checked={toggleValue}
                onChange={setToggleValue}
                label="Email notifications"
              />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Notification Volume
                </label>
                <Slider
                  value={sliderValue}
                  onChange={(val) => setSliderValue(typeof val === 'number' ? val : val[0])}
                  min={0}
                  max={100}
                  showValue
                />
              </div>
            </div>
          </FormField>
          <div className="flex gap-2 items-center">
            <Button onClick={() => alert('Saved!')}>Save Settings</Button>
            <Badge variant="success" icon={<CheckCircle className="w-3 h-3" />}>
              All changes saved
            </Badge>
          </div>
        </CardBody>
      </Card>
    </div>
  )
}

