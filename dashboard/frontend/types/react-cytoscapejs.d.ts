declare module 'react-cytoscapejs' {
  import { Component } from 'react';
  import { Core, ElementDefinition, StylesheetCSS, LayoutOptions } from 'cytoscape';

  export interface CytoscapeComponentProps {
    elements: ElementDefinition[];
    style?: React.CSSProperties;
    stylesheet?: StylesheetCSS[];
    layout?: LayoutOptions;
    cy?: (cy: Core) => void;
    minZoom?: number;
    maxZoom?: number;
    wheelSensitivity?: number;
  }

  export default class CytoscapeComponent extends Component<CytoscapeComponentProps> {}
}