import renderer from 'react-test-renderer';
import { QuotaOriginFormset } from '../index';

it('formset renders with props', () => {

  const mockOriginsErrors = {}

  const mockOrigins = [
    {
      "id": 1,
      "exclusions": [
        { "id": 3 },
        { "id": 4 },
      ],
      "geographical_area": 1,
      "start_date_0": 1,
      "start_date_1": 1,
      "start_date_2": 2000,
      "end_date_0": 1,
      "end_date_1": 1,
      "end_date_2": 2010,
    },
    {
      "id": 2,
      "exclusions": [
        { "id": 5 },
      ],
      "geographical_area": 2,
      "start_date_0": 1,
      "start_date_1": 1,
      "start_date_2": 2000,
      "end_date_0": 1,
      "end_date_1": 1,
      "end_date_2": 2010,
    },
  ]

  const mockGeoAreaOptions = [
    {
      "name": "All countries",
      "value": 1
    },
    {
      "name": "EU",
      "value": 2
    },
    {
      "name": "China",
      "value": 3
    },
    {
      "name": "South Korea",
      "value": 4
    },
    {
      "name": "Switzerland",
      "value": 5
    },
  ]

  const component = renderer.create(
    <QuotaOriginFormset data={mockOrigins} options={mockGeoAreaOptions} errors={mockOriginsErrors} />,
  );

  let tree = component.toJSON();
  expect(tree).toMatchSnapshot();

  // // manually trigger the callback
  // renderer.act(() => {
  //   tree.props.onMouseEnter();
  // });
  // // re-rendering
  // tree = component.toJSON();
  // expect(tree).toMatchSnapshot();

  // // manually trigger the callback
  // renderer.act(() => {
  //   tree.props.onMouseLeave();
  // });
  // // re-rendering
  // tree = component.toJSON();
  // expect(tree).toMatchSnapshot();
});
