import React from 'react';
import { render, fireEvent } from '@testing-library/react';
import ChatApp from '../src/ChatApp';

test('renders chat app and starts session', () => {
  const { getByText } = render(<ChatApp />);
  const startButton = getByText('Start Chat Session');
  expect(startButton).toBeInTheDocument();
});
