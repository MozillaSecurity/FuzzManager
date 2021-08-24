import {render, fireEvent} from '@testing-library/vue'
import Inbox from '../src/components/Notifications/Inbox.vue'

test('inbox has no notifications', async () => {
  const {getByText} = render(Inbox)
  getByText('Unread notifications')
})
