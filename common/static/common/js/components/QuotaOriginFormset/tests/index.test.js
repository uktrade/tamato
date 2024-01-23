import renderer from 'react-test-renderer';
import { QuotaOriginFormset } from '../index';

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

const mockOrigins = [
  {
    "id": 1,
    "pk": 1,
    "exclusions": [
      { "id": 3, "pk": 1 },
      { "id": 4, "pk": 2 },
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
    "pk": 2,
    "exclusions": [
      { "id": 5, "pk": 3 },
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


it('renders formset with props', () => {

  const mockOriginsErrors = {}

  const component = renderer.create(
    <QuotaOriginFormset data={mockOrigins} options={mockGeoAreaOptions} errors={mockOriginsErrors} />,
  );

  let tree = component.toJSON();
  expect(tree).toMatchSnapshot();

});

it('renders empty formset when no initial data', () => {

  const mockOriginsErrors = {}
  const mockOrigins = []

  const component = renderer.create(
    <QuotaOriginFormset data={mockOrigins} options={mockGeoAreaOptions} errors={mockOriginsErrors} />,
  );

  let tree = component.toJSON();
  expect(tree).toMatchSnapshot();

});

it('renders with formset errors', () => {

  const mockOriginsErrors = {
    "origins-0-end_date": "The end date must be the same as or after the start date.",
  };

  const component = renderer.create(
    <QuotaOriginFormset data={mockOrigins} options={mockGeoAreaOptions} errors={mockOriginsErrors} />,
  );

  let tree = component.toJSON();
  expect(tree).toMatchSnapshot();

});
